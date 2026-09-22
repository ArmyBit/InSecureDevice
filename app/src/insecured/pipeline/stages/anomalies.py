from __future__ import annotations

from collections import Counter

from insecured.pipeline.base import Stage, StageContext


class AnomalyStage(Stage):
    """Stage 4 - détection d'anomalies.

    Croise les données produites par les stages précédents (hash, extension,
    taille) pour signaler les fichiers suspects : doublons exacts masqués par
    des noms/extensions différents, fichiers vides notés 'document', etc.
    """

    name = "anomalies"

    def run(self, ctx: StageContext) -> dict:
        anomalies = []
        by_hash: dict[str, list] = {}
        for f in ctx.files:
            by_hash.setdefault(f.sha256, []).append(f)

        for h, group in by_hash.items():
            if h and len(group) > 1:
                names = {g.path.name for g in group}
                if len(names) > 1:
                    for g in group:
                        g.anom = (g.anom + "; doublon masqué" if g.anom else "doublon masqué")
                    anomalies.append(f"hash {h[:8]}… → {len(group)} fichiers sous {len(names)} noms")

        for f in ctx.files:
            if f.size == 0 and f.magic == "Fichier vide":
                continue
            if f.size == 0 and f.mime not in ("", "application/octet-stream"):
                f.anom = (f.anom + "; fichier vide classé" if f.anom else "fichier vide classé")
                anomalies.append(f"{f.path} vide mais annoncé {f.mime}")

        ctx.data["anomalies"] = anomalies
        return {"status": "ok", "anomalies": anomalies, "count": len(anomalies)}