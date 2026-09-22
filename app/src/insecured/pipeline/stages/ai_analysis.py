from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod

from insecured.pipeline.base import Stage, StageContext
from insecured.pipeline.stages.disasm import extract_assembly


def build_ai_backend():
    """Construit le backend IA selon la configuration (openai/ollama/dev/cli)."""
    from insecured.config import get_settings

    s = get_settings()
    if s.ai_backend == "openai":
        return OpenAIBackend(base_url=s.ai_base_url, model=s.ai_model)
    if s.ai_backend == "ollama":
        return OllamaBackend(model=s.ai_model)
    if s.ai_backend == "cli":
        return CLIBackend([s.ai_model])
    return DevAIBackend()


class AIBackend(ABC):
    """Interface du moteur IA on-premise (air-gapped).

    Deux implémentations : un backend CLI (ex. Ollama / llama.cpp en local)
    et un backend dev qui renvoie un texte de démonstration sans IA réelle.
    """

    @abstractmethod
    def analyze(self, prompt: str, max_tokens: int | None = None) -> str:
        ...


class OllamaBackend(AIBackend):
    """Backend IA local : requête Ollama (http://localhost:11434)."""

    def __init__(self, model: str = "qwen2.5-coder", url: str = "http://localhost:11434/api/generate"):
        self.model = model
        self.url = url

    def analyze(self, prompt: str, max_tokens: int | None = None) -> str:
        import urllib.request

        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "num_predict": max_tokens or 256,
            }
        ).encode()
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response", "")


class OpenAIBackend(AIBackend):
    """Backend IA local : API compatible OpenAI (ex. LM Studio, llama.cpp).

    Pointage sur http(s)://<hôte>:<port>/v1/chat/completions avec un modèle
    au nom qualifié ex. "qwen/qwen2.5-coder-14b".
    """

    def __init__(
        self,
        base_url: str = "http://10.8.0.2:1234",
        model: str = "qwen/qwen2.5-coder-14b",
        timeout: int = 180,
        max_tokens: int = 1500,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def analyze(self, prompt: str, max_tokens: int | None = None) -> str:
        import urllib.request

        url = f"{self.base_url}/v1/chat/completions"
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "stream": False,
                "max_tokens": max_tokens or self.max_tokens,
            }
        ).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            payload = json.loads(r.read())
        return payload["choices"][0]["message"]["content"]


class CLIBackend(AIBackend):
    """Backend IA local : exécute un binaire CLI fournissant un modèle."""

    def __init__(self, cmd: list[str]):
        self.cmd = cmd

    def analyze(self, prompt: str, max_tokens: int | None = None) -> str:
        out = subprocess.run(self.cmd + [prompt], capture_output=True, text=True, timeout=300)
        return out.stdout.strip()


class DevAIBackend(AIBackend):
    """Backend de développement : aucun réseau, sortie simulée."""

    def analyze(self, prompt: str, max_tokens: int | None = None) -> str:
        return " [DEV] Analyse simulée (aucun modèle local disponible)."


class AIAnalysisStage(Stage):
    """Stage 6 - analyse & reverse engineering assistés par IA (on-premise).

    Envoie à l'IA uniquement les fichiers suspects. Réponse volontairement
    courte (max_tokens limité) pour ne pas bloquer la pipeline sur un LLM lent.
    """

    name = "ai_analysis"

    def __init__(self, backend: AIBackend, max_tokens: int = 250) -> None:
        self.backend = backend
        self.max_tokens = max_tokens

    def run(self, ctx: StageContext) -> dict:
        targets = [f for f in ctx.files if f.anom]
        if not targets:
            return {"status": "skip", "message": "aucun fichier suspect", "hits": []}

        hits = []
        for f in targets:
            self._report(f"IA : {f.path.name} — envoi au LLM local…", None)
            asm, asm_err = extract_assembly(f.path)
            if asm_err:
                asm_err_ctx = f"(désassemblage indisponible : {asm_err})"
            else:
                asm_err_ctx = ""
            prompt = (
                f"Analyse forensique d'un fichier suspect. Chemin: {f.path}\n"
                f"Taille: {f.size} octets, SHA-256: {f.sha256}\n"
                f"Type détecté: {f.magic} ({f.mime})\n"
                f"Anomalie: {f.anom} {asm_err_ctx}\n"
            )
            if asm:
                prompt += (
                    f"\nExtrait assembleur du fichier (désassemblé) :\n"
                    f"```asm\n{asm}\n```\n"
                )
            prompt += (
                "Propose une hypothèse sur le contenu, le comportement (appels système, "
                f"strings cryptées, sections suspectes) et les risques "
                "en 3 à 5 lignes maximum."
            )
            try:
                f.notes = self._bounded_analyze(f.path.name, prompt)
            except Exception as exc:  # l'IA ne doit jamais bloquer la pipeline
                f.notes = f"[erreur IA] {exc}"
            hits.append({"path": str(f.path), "notes": f.notes, "asm_len": len(asm)})
            self._report(f"IA : {f.path.name} ✓", None)
        ctx.data["ai_hits"] = hits
        return {"status": "ok", "hits": hits}

    def _bounded_analyze(self, name: str, prompt: str) -> str:
        """Appel IA borné : ne dépasse jamais ``self.timeout_per_file``.

        Le backend peut être lent ou accroché ; on ne laisse jamais un fichier
        bloquer la pipeline indéfiniment (garde-fou via ThreadPoolExecutor).
        """
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.backend.analyze, prompt, self.max_tokens)
            try:
                return future.result(timeout=self.timeout_per_file)
            except TimeoutError:
                return "[timeout] LLM local trop lent — analyse interrompue."