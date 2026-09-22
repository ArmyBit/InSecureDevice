# Configuration de l'environnement.
#
# QUBES_BACKEND:
#   "dev" (défaut) - aucun Qubes nécessaire, workflow de dev utilisant
#                    le dossier DEV_MEDIA comme "média connecté".
#   "qvm"          - vrai poste Qubes OS (qvm-block dans dom0 / sys-usb).
#
# AI_BACKEND:
#   "dev"   - sortie simulée, aucun réseau.
#   "ollama"- modèle local via Ollama (on-premise, air-gapped).
#   "openai"- API compatible OpenAI (LM Studio / llama.cpp) locale.
#   "cli"   - binaire CLI local.
#
# AI_MODEL: nom du modèle (utilisé par les backends ollama et openai).
# AI_BASE_URL: base URL du serveur compatible OpenAI (utilisée si AI_BACKEND="openai").
#
# VT_BACKEND:
#   "dev" (défaut) - aucune requête réseau, sortie simulée.
#   "api"          - vraie API VirusTotal v3.
#
# VT_API_KEY: clé API VirusTotal (obligatoire si VT_BACKEND="api").
#   À fournir par variable d'environnement — ne jamais versionner la clé.

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    qubes_backend: str
    ai_backend: str
    ai_model: str
    media_root: str
    vt_backend: str = "dev"
    vt_api_key: str = ""
    ai_base_url: str = "http://10.8.0.2:1234"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            qubes_backend=os.environ.get("QUBES_BACKEND", "dev"),
            ai_backend=os.environ.get("AI_BACKEND", "openai"),
            ai_model=os.environ.get("AI_MODEL", "qwen/qwen2.5-coder-14b"),
            ai_base_url=os.environ.get("AI_BASE_URL", "http://10.8.0.2:1234"),
            media_root=os.environ.get("DEV_MEDIA", "DEV_MEDIA"),
            vt_backend=os.environ.get("VT_BACKEND", "dev"),
            vt_api_key=os.environ.get("VT_API_KEY", "").strip(),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings