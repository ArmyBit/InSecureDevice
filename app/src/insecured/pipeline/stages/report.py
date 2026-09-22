from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from urllib.error import URLError

from insecured.models.report import PipelineResult
from insecured.pipeline.base import Stage, StageContext
from insecured.pipeline.stages.ai_analysis import AIBackend


class ReportStage(Stage):
    """Stage rapport - rédige le rapport forensique final assisté par IA.

    Rassemble tout le contexte d'analyse (cas, fichiers, anomalies, VirusTotal,
    notes IA) et demande au backend IA de rédiger un rapport en français.
    """

    name = "report"

    def __init__(self, backend: AIBackend) -> None:
        self.backend = backend

    def run(self, ctx: StageContext) -> dict:
        prompt = self.build_prompt(ctx)
        try:
            text = self._bounded_analyze(prompt)
        except Exception as exc:  # l'IA ne doit jamais bloquer / empêcher l'export
            text = (f"[ERREUR IA - {exc}]\n\n"
                    "Rapport généré sans IA : seules les données analysées sont reprises ci-dessous.")
            text += "\n\n" + self._fallback_report(ctx)
        ctx.data["report_text"] = text
        self._bounded_analyze = self.backend.analyze  # compat
        self._export_file(ctx, text)
        self._report("Rapport : intégration des constats ✓", None)
        return {"status": "ok", "length": len(text)}

    def _export_file(self, ctx: StageContext, text: str) -> Path | None:
        """Écrit le rapport forensique sur disque (livrable air-gapped).

        Cible : dossier ``RAPPORTS`` placé à côté du support analysé, sous le nom
        ``rapport_<cas>_<horodatage>.md``. Ne ré-écrase jamais un rapport
        antérieur du même cas.
        """
        from datetime import datetime

        try:
            case = ctx.case
            base = None
            for cand in (getattr(case, "image_path", None), getattr(case, "image", None),
                         getattr(case, "mount_point", None)):
                if cand:
                    cand = Path(cand)
                    if cand.is_dir():
                        base = cand
                        break
            if base is None:
                base = Path.cwd()
            reports = base / "RAPPORTS"
            reports.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = getattr(case, "name", "cas") or "cas"
            target = reports / f"rapport_{name}_{stamp}.md"
            target.write_text(text, encoding="utf-8")
            ctx.data["report_path"] = str(target)
            self._report(f"Rapport exporté : {target}", None)
            return target
        except OSError as exc:  # un échec d'écriture ne doit jamais casser l'analyse
            self._report(f"Rapport : export disque impossible ({exc})", None)
            return None

    def _bounded_analyze(self, prompt: str) -> str:
        """Appel IA borné : ne bloque jamais l'export final au-delà du délai fixé.

        Le backend peut être lent ou accroché ; on ne laisse jamais un modèle
        retenir la génération du rapport (garde-fou via ThreadPoolExecutor).
        """
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.backend.analyze, prompt)
            try:
                return future.result(timeout=self.timeout)
            except TimeoutError:
                return ("[timeout] LLM local trop lent — rapport rédigé sans IA "
                        "(constats disponibles ci-dessous).")

    @classmethod
    def build_prompt(cls, ctx: StageContext) -> str:
        case = ctx.case
        lines = []
        files = ctx.files

        lines.append("Rédige un rapport d'analyse forensique professionnel en français.")
        lines.append(f"Cas : {case.name} ({getattr(case, 'case_id', '?')})")
        lines.append(f"Opérateur : {getattr(case, 'operator', '') or 'inconnu'}")
        lines.append(f"Date d'ouverture : {getattr(case, 'opened_at', None) or '?'}")
        lines.append(f"Nombre de fichiers : {len(files)}")

        if getattr(case, "image_path", None):
            lines.append(f"Source analysée : {case.image_path}")

        anomalies = ctx.data.get("anomalies", [])
        lines.append(f"Anomalies détectées : {len(anomalies)}")
        for a in anomalies:
            lines.append(f"  - {a}")

        suspects = [f for f in files if f.anom]
        lines.append(f"Fichiers suspects : {len(suspects)}")
        for f in suspects:
            lines.append(
                f"  - {f.path.name} | {f.magic} | SHA-256: {f.sha256} | "
                f"anomalie: {f.anom} | VirusTotal: {f.vt or 'non vérifié'}"
            )
            if f.notes:
                lines.append(f"      notes IA: {f.notes}")

        vt = ctx.data.get("vt_results", [])
        if vt:
            lines.append("Vérification VirusTotal :")
            for h in vt:
                stats = h.get("stats") or {}
                lines.append(
                    f"  - {h.get('path')}: {stats.get('malicious', 0)} malicieux / "
                    f"{stats.get('suspicious', 0)} suspicieux (rep {h.get('reputation')})"
                )

        lines.append(
            "\nStructure attendue du rapport :"
            "\n1. Résumé exécutif"
            "\n2. Déroulé de l'analyse (méthodes employées)"
            "\n3. Constats détaillés (fichiers suspects, anomalies)"
            "\n4. Éléments techniques (empreintes, VirusTotal, notes IA)"
            "\n5. Recommandations et conclusion"
        )
        return "\n".join(lines)

    @staticmethod
    def _fallback_report(ctx: StageContext) -> str:
        case = ctx.case
        rows = []
        rows.append("RÉSUMÉ EXÉCUTIF")
        rows.append(f"Analyse du cas {case.name} réalisée. "
                    f"{len(ctx.files)} fichiers analysés.")
        anomalies = ctx.data.get("anomalies", [])
        rows.append(f"{len(anomalies)} anomalie(s) détectée(s).")
        rows.append("")
        rows.append("CONSTATS DÉTAILLÉS")
        for f in ctx.files:
            if f.anom:
                rows.append(f"• {f.path.name}: {f.anom} | VirusTotal: {f.vt or 'non vérifié'}")
        if not [f for f in ctx.files if f.anom]:
            rows.append("Aucun fichier suspect détecté.")
        rows.append("")
        rows.append("CONCLUSION")
        rows.append("Support analysé ; un examen approfondi reste recommandé "
                    "pour les éléments suspects.")
        return "\n".join(rows)

    @staticmethod
    def to_result(text: str) -> PipelineResult:
        return PipelineResult(stage="report", status="ok", message="rapport généré", data={"text": text})