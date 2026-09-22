from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from insecured.pipeline.base import StageContext
from insecured.pipeline.stages.ai_analysis import AIBackend
from insecured.pipeline.stages.report import ReportStage
from insecured.models.session import CaseSession
from insecured.ui.evidence_view import EvidenceTable
from insecured.ui.file_dialog import FileInfoDialog
from insecured.ui.stats_view import StatsView
from insecured.ui.steps_view import STEP_ORDER, StepsView

STATUS_META = {
    "running": ("● En cours", "#f1c40f"),
    "done": ("✓ Terminé", "#2ecc71"),
    "error": ("✕ Échec", "#e74c3c"),
}


class ReportWorker(QObject):
    """Génère le rapport IA dans un thread (ne bloque pas l'interface)."""

    finished = Signal(str)      # texte du rapport
    failed = Signal(str)

    def __init__(self, session: CaseSession, backend: AIBackend) -> None:
        super().__init__()
        self._session = session
        self._backend = backend

    def run(self) -> None:
        try:
            ctx = StageContext(
                case=self._session.case,
                files=self._session.files,
                data={},
            )
            for r in self._session.results:
                ctx.data.update(r.data or {})
            prompt = ReportStage(self._backend).build_prompt(ctx)
            report = self._backend.analyze(prompt)
            self.finished.emit(report)
        except Exception as exc:
            self.failed.emit(str(exc))


class CaseDetailView(QWidget):
    """Vue détaillée d'une analyse : stepper, KPI, table, journal."""

    backRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.back_button = QPushButton("←  Retour au tableau de bord")
        self.back_button.setObjectName("backButton")
        self.back_button.clicked.connect(self.backRequested)

        self.title = QLabel("")
        self.title.setObjectName("detailTitle")
        self.badge = QLabel("")
        self.badge.setObjectName("detailBadge")

        head = QHBoxLayout()
        head.addWidget(self.back_button)
        head.addStretch(1)
        head.addWidget(self.badge)

        info = QLabel("")
        info.setObjectName("detailInfo")

        self.stats = StatsView()
        self.report_button = QPushButton("✍  Générer un rapport (IA)")
        self.report_button.setObjectName("reportButton")
        self.report_button.setCursor(Qt.PointingHandCursor)
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self._generate_report)
        self.report_status = QLabel("")
        self.report_status.setObjectName("reportStatus")
        self.summary = QLabel("")
        self.summary.setObjectName("summary")
        self.verdict = QLabel("")
        self.verdict.setObjectName("verdict")

        self.steps = StepsView()
        steps_card = QFrame()
        steps_card.setObjectName("card")
        steps_box = QVBoxLayout(steps_card)
        steps_box.setContentsMargins(10, 10, 10, 10)
        steps_box.addWidget(self.steps)

        self.table = EvidenceTable()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(110)

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self.stats)
        action_row = QHBoxLayout()
        action_row.addWidget(self.report_button, 0)
        action_row.addWidget(self.report_status, 1)
        right.addLayout(action_row)
        right.addWidget(self.summary)
        right.addWidget(self.verdict)
        right.addWidget(self.table, 1)
        right.addWidget(self.log)

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(steps_card, 0)
        body.addLayout(right, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)
        lay.addLayout(head)
        lay.addWidget(self.title)
        lay.addWidget(info)
        lay.addLayout(body, 1)

        self._info = info
        self.session: CaseSession | None = None
        self.ai_backend: AIBackend | None = None
        self._report_thread: QThread | None = None
        self._report_worker: ReportWorker | None = None
        self.table.rowClicked.connect(self._open_file)

    def set_ai_backend(self, backend: AIBackend) -> None:
        self.ai_backend = backend

    # ------------------------------------------------------------- display
    def show_session(self, session: CaseSession) -> None:
        self.session = session
        self.title.setText(session.case.name)
        stext, scolor = STATUS_META.get(session.status, STATUS_META["running"])
        self.badge.setText(stext)
        self.badge.setStyleSheet(f"color: {scolor}; font-weight: 700; font-size: 13px;")
        self._info.setText(
            f"{session.case.case_id}  ·  opérateur : {session.case.operator or '—'}  ·  "
            f"montage : {session.mount_point or '—'}  ·  début : {self._dt(session.started_at)}"
            + (f"  ·  fin : {self._dt(session.finished_at)}" if session.finished_at else "")
        )
        self._info.setStyleSheet("color: #6b7488; font-size: 12px;")

        for row in self.steps.rows:
            row.set_state("pending")
        for stage, state in session.stages.items():
            if stage in STEP_ORDER:
                self.steps.set_state(STEP_ORDER.index(stage), state)

        total, safe, suspects = session.counts
        self.stats.update_counts(total, safe, suspects, session.anomalies)
        if session.is_running:
            self.summary.setText("Analyse en cours…")
            self.verdict.setText("")
            self.report_button.setEnabled(False)
        else:
            self.summary.setText(
                f"Analyse terminée — {total} fichiers · {safe} sains · {suspects} suspects · {session.anomalies} anomalies"
            )
            self._set_verdict(suspects == 0)
            self.report_button.setEnabled(True)
            if session.report_text:
                self.report_status.setText("✓ Rapport généré")
                try:
                    self.report_status.setStyleSheet("color: #2ecc71; font-weight: 600; font-size: 12px;")
                except Exception:
                    pass

        self.table.load(session.files)

        log_text = "\n".join(session.logs)
        self.log.setPlainText(log_text)

    def refresh(self) -> None:
        if self.session is not None:
            self.show_session(self.session)

    def _set_verdict(self, clean: bool) -> None:
        if clean:
            self.verdict.setStyleSheet("color: #2ecc71; font-weight: 700; font-size: 14px;")
            self.verdict.setText("✓ AUCUNE ANOMALIE DÉTECTÉE — support considéré sain")
        else:
            self.verdict.setStyleSheet("color: #e74c3c; font-weight: 700; font-size: 14px;")
            self.verdict.setText("⚠ SUSPECTS DÉTECTÉS — examen approfondi requis")

    def _open_file(self, evidence) -> None:
        FileInfoDialog(evidence, self).exec()

    def _generate_report(self) -> None:
        if self.session is None or self.ai_backend is None:
            return
        self.report_button.setEnabled(False)
        self.report_button.setText("Rédaction en cours…")
        self.report_status.setText("L'IA rédige le rapport…")
        self.report_status.setStyleSheet("color: #f1c40f; font-weight: 600; font-size: 12px;")

        thread = QThread(self)
        worker = ReportWorker(self.session, self.ai_backend)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_report_ready)
        worker.failed.connect(self._on_report_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        self._report_thread = thread
        thread.start()

    def _on_report_ready(self, text: str) -> None:
        if self.session is not None:
            self.session.report_text = text
            self.session.stages["report"] = "done"
        self.report_button.setEnabled(True)
        self.report_button.setText("✍  Régénérer le rapport (IA)")
        self.report_status.setText("✓ Rapport généré")
        self.report_status.setStyleSheet("color: #2ecc71; font-weight: 600; font-size: 12px;")
        self.log.setPlainText(text)

    def _on_report_failed(self, message: str) -> None:
        self.report_button.setEnabled(True)
        self.report_button.setText("✍  Générer un rapport (IA)")
        self.report_status.setText("Échec de la génération")
        self.report_status.setStyleSheet("color: #e74c3c; font-weight: 600; font-size: 12px;")
        self.log.append(f"\n\n[ERREUR IA] {message}")

    def closeEvent(self, event) -> None:
        if self._report_thread is not None and self._report_thread.isRunning():
            self._report_thread.quit()
            self._report_thread.wait(3000)
        super().closeEvent(event)

    @staticmethod
    def _dt(value) -> str:
        if not value:
            return "?"
        return value.strftime("%Y-%m-%d %H:%M:%S")