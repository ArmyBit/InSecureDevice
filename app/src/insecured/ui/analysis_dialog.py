from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from insecured.models.case import Case
from insecured.pipeline.base import StageContext
from insecured.pipeline.orchestrator import Orchestrator
from insecured.pipeline.stages import (
    AnomalyStage,
    AIAnalysisStage,
    DevVTBackend,
    HashStage,
    InventoryStage,
    MetadataStage,
    MountStage,
    VTStage,
    VirusTotalBackend,
)
from insecured.config import get_settings
from insecured.ui.steps_view import StepsView
from insecured.ui.theme import GlassDialog, glass_stylesheet


def build_vt_backend():
    """Retourne le backend VirusTotal : API réelle si une clé est présente, sinon dev."""
    settings = get_settings()
    if settings.vt_api_key:
        return VirusTotalBackend(settings.vt_api_key)
    return DevVTBackend()


class AnalysisWorker(QObject):
    """Exécute la pipeline dans un thread, émet des signaux par étape."""

    stage_started = Signal(str)
    stage_ended = Signal(str, str)  # (stage, état)
    message = Signal(str, int)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, case: Case, mount: str, bridge, ai_backend) -> None:
        super().__init__()
        self._case = case
        self._mount = mount
        self._bridge = bridge
        self._ai_backend = ai_backend
        self.ctx: StageContext | None = None
        self.results = []

    def run(self) -> None:
        try:
            ctx = StageContext(
                case=self._case,
                progress=lambda msg, p: self.message.emit(msg, p or 0),
            )
            orch = (
                Orchestrator()
                .add_stage(MountStage(mount_point=self._mount, bridge=self._bridge))
                .add_stage(InventoryStage(mount_point=self._mount))
                .add_stage(HashStage())
                .add_stage(MetadataStage())
                .add_stage(AnomalyStage())
                .add_stage(VTStage(backend=build_vt_backend()))
                .add_stage(AIAnalysisStage(backend=self._ai_backend))
            )
            orch.on_stage_start = lambda s: self.stage_started.emit(s)
            orch.on_stage_end = lambda s, r: self.stage_ended.emit(s, r.status)
            self.results = orch.run(ctx)
            self.ctx = ctx
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class AnalysisDialog(GlassDialog):
    """Dialog modal : stepper du process + progression pendant l'analyse."""

    STAGE_INDEX = {
        "mount": 0,
        "inventory": 1,
        "hashing": 2,
        "metadata": 3,
        "anomalies": 4,
        "vt_check": 5,
        "ai_analysis": 6,
        "report": 7,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Analyse en cours")
        self.setModal(True)
        self.setMinimumSize(480, 560)

        title = QLabel("Analyse du support")
        title.setObjectName("dialogTitle")

        self.steps = StepsView()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status = QLabel("Démarrage…")
        self.status.setObjectName("dialogStatus")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)

        self.close_button = QPushButton("Fermer")
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.addWidget(title)
        lay.addWidget(self.steps)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)
        lay.addWidget(self.log)
        lay.addWidget(self.close_button)

        self.setStyleSheet(
            glass_stylesheet()
            + """
            GlassDialog { background: transparent; }
            QLabel#dialogTitle { color: #fff; font-size: 16px; font-weight: 700; }
            QLabel#dialogStatus { color: #f1c40f; font-weight: 600; }
            """
        )

    # ------------------------------------------------------------- hooks
    def on_stage_start(self, stage: str) -> None:
        idx = self.STAGE_INDEX.get(stage)
        if idx is not None:
            self.steps.set_state(idx, "running")
            self.status.setText(self.steps.STEP_LABELS[idx])

    def on_stage_end(self, stage: str, state: str) -> None:
        idx = self.STAGE_INDEX.get(stage)
        if idx is None:
            return
        status = "done" if state != "error" else "error"
        self.steps.set_state(idx, status)

    def on_message(self, msg: str, progress: int) -> None:
        self.log.append(msg)
        self.progress.setValue(progress)

    def finish(self) -> None:
        idx = self.STAGE_INDEX.get("report")
        if idx is not None:
            self.steps.set_state(idx, "done")
        self.progress.setValue(100)
        self.status.setStyleSheet("color: #2ecc71; font-weight: 600;")
        self.status.setText("Analyse terminée")
        self.log.append("— Fin du process —")
        self.close_button.setVisible(True)

    def set_error(self, message: str) -> None:
        self.status.setStyleSheet("color: #e74c3c; font-weight: 600;")
        self.status.setText("Échec de l'analyse")
        self.log.append(f"[ERREUR] {message}")
        self.close_button.setVisible(True)