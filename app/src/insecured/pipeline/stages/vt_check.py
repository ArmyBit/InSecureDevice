from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from insecured.pipeline.base import Stage, StageContext


class VTBackend(ABC):
    """Interface de vérification VirusTotal (par empreinte SHA-256)."""

    @abstractmethod
    def check(self, sha256: str) -> dict:
        ...


class VirusTotalBackend(VTBackend):
    """Backend API officiel VirusTotal v3 (nécessite VT_API_KEY).

    GET https://www.virustotal.com/api/v3/files/{sha256}
    """

    BASE = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str, timeout: int = 30) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def check(self, sha256: str) -> dict:
        req = urllib.request.Request(
            f"{self.BASE}/files/{sha256}",
            headers={"x-apikey": self.api_key, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {"found": False, "raw": {"error": "not found"}}
            return {"found": False, "error": f"HTTP {exc.code}", "raw": {}}
        except Exception as exc:
            return {"found": False, "error": str(exc), "raw": {}}

        attrs = payload.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})
        engines = attrs.get("last_analysis_results", {})
        return {
            "found": True,
            "stats": {
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless": stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
                "timeout": stats.get("timeout", 0),
                "type_unsupported": stats.get("type-unsupported", 0),
            },
            "engines": [
                {
                    "name": name,
                    "category": meta.get("category"),
                    "result": meta.get("result"),
                }
                for name, meta in engines.items()
                if meta.get("category") in ("malicious", "suspicious") and meta.get("result")
            ],
            "reputation": attrs.get("reputation", 0),
            "times_submitted": attrs.get("times_submitted", 0),
            "meaningful_name": attrs.get("meaningful_name", ""),
            "first_seen": attrs.get("first_submission_date"),
            "last_analysis_date": attrs.get("last_analysis_date"),
            "raw": attrs,
        }


class DevVTBackend(VTBackend):
    """Backend de développement : aucun réseau, sortie simulée (air-gap)."""

    def check(self, sha256: str) -> dict:
        return {
            "found": False,
            "dev": True,
            "error": "backend dev — aucune requête VirusTotal effectuée",
        }


class VTStage(Stage):
    """Stage 6 - vérification des empreintes SHA-256 sur VirusTotal."""

    name = "vt_check"

    def __init__(self, backend: VTBackend, threshold: int = 1) -> None:
        self.backend = backend
        self.threshold = threshold

    def run(self, ctx: StageContext) -> dict:
        targets = [f for f in ctx.files if f.sha256]
        if not targets:
            return {"status": "skip", "message": "aucune empreinte SHA-256", "hits": []}

        hits = []
        anomalies = list(ctx.data.get("anomalies", []))
        for f in targets:
            try:
                rep = self.backend.check(f.sha256)
            except Exception as exc:  # ne doit jamais bloquer la pipeline
                rep = {"found": False, "error": str(exc)}

            f.vt = self._summarize(rep)
            malicious = rep.get("stats", {}).get("malicious", 0) if rep.get("found") else 0
            if malicious >= self.threshold:
                f.anom = (f.anom + "; VirusTotal" if f.anom else "VirusTotal")
                anomalies.append(
                    f"{f.path.name} → {malicious} moteur(s) malveillant(s) "
                    f"(reputation {rep.get('reputation')})"
                )
            hits.append(
                {
                    "path": str(f.path),
                    "sha256": f.sha256,
                    "found": rep.get("found", False),
                    "stats": rep.get("stats"),
                    "reputation": rep.get("reputation"),
                    "summary": f.vt,
                }
            )
            self._report(f"VirusTotal : {f.path.name}", None)

        ctx.data["anomalies"] = anomalies
        ctx.data["vt_results"] = hits
        return {"status": "ok", "hits": hits, "count": len(hits)}

    @staticmethod
    def _summarize(rep: dict) -> str:
        if rep.get("dev"):
            return "non vérifié (dev)"
        if not rep.get("found"):
            return "non référencé" if "HTTP" in rep.get("error", "error") or rep.get("raw", {}).get("error") == "not found" else (
                "⚠ analyse impossible"
            )
        stats = rep.get("stats", {})
        m, s = stats.get("malicious", 0), stats.get("suspicious", 0)
        if m or s:
            return f"⚠ {m} malicieux / {s} suspicieux"
        return "✓ sain (0 détection)"