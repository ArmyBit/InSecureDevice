from __future__ import annotations

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from insecured.models.case import Case
from insecured.models.session import CaseSession
from insecured.pipeline.stages.ai_analysis import build_ai_backend
from insecured.qubes import build_bridge
from insecured.ui.analysis_dialog import AnalysisDialog, AnalysisWorker
from insecured.ui.case_dashboard import CaseDashboard
from insecured.ui.case_detail import CaseDetailView
from insecured.ui.new_case_dialog import NewCaseDialog
from insecured.ui.theme import GlassWidget, glass_stylesheet


class MainWindow(QMainWindow):
    """Dashboard professionnel : cartes d'analyses, détail par carte."""

    def __init__(self, bridge=None, ai_backend=None) -> None:
        super().__init__()
        self.setWindowTitle("InSecureDevice — Console forensique isolée")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1280, 820)
        self.bridge = bridge or build_bridge()
        self.ai_backend = ai_backend or build_ai_backend()
        self.sessions: list[CaseSession] = []
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None

        root = GlassWidget()
        root.setObjectName("root")
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_header())
        self.stack = QStackedWidget()
        self.dashboard = CaseDashboard()
        self.detail = CaseDetailView()
        self.detail.set_ai_backend(self.ai_backend)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.detail)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.dashboard.newAnalysisRequested.connect(self._run_pipeline)
        self.dashboard.cardClicked.connect(self._open_case)
        self.detail.backRequested.connect(lambda: self.stack.setCurrentWidget(self.dashboard))
        self._apply_style()

    # ------------------------------------------------------------------ UI
    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 10, 12, 10)
        title = QLabel("IN SECURE DEVICE")
        title.setObjectName("appTitle")
        subtitle = QLabel("Console forensique statique · qubes isolés")
        subtitle.setObjectName("appSubtitle")
        badge = QLabel("● SYSTÈME PRÊT")
        badge.setObjectName("readyBadge")
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addStretch(1)
        lay.addWidget(badge, 0, Qt.AlignVCenter)
        lay.addSpacing(10)

        self.win_min = QPushButton("—")
        self.win_min.setObjectName("winBtn")
        self.win_min.setFixedSize(34, 28)
        self.win_min.setCursor(Qt.PointingHandCursor)
        self.win_min.clicked.connect(self.showMinimized)

        self.win_max = QPushButton("□")
        self.win_max.setObjectName("winBtn")
        self.win_max.setFixedSize(34, 28)
        self.win_max.setCursor(Qt.PointingHandCursor)
        self.win_max.clicked.connect(self._toggle_maximize)

        self.win_close = QPushButton("✕")
        self.win_close.setObjectName("winClose")
        self.win_close.setFixedSize(34, 28)
        self.win_close.setCursor(Qt.PointingHandCursor)
        self.win_close.clicked.connect(self.close)

        lay.addWidget(self.win_min, 0, Qt.AlignVCenter)
        lay.addWidget(self.win_max, 0, Qt.AlignVCenter)
        lay.addWidget(self.win_close, 0, Qt.AlignVCenter)

        header.mousePressEvent = self._drag_start
        header.mouseMoveEvent = self._drag_move
        header.mouseDoubleClickEvent = lambda _e: self._toggle_maximize()
        return header

    def _drag_start(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _drag_move(self, event) -> None:
        if event.buttons() & Qt.LeftButton and getattr(self, "_drag_pos", None) is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _apply_style(self) -> None:
        self.setStyleSheet(glass_stylesheet())

    # -------------------------------------------------------------- sessions
    def _new_session(self, name: str, operator: str, mount: str) -> CaseSession:
        case = Case(name=name, image_path=mount, operator=operator)
        session = CaseSession(case=case, mount_point=mount)
        self.sessions.append(session)
        self.dashboard.set_sessions(self.sessions)
        return session

    def _open_case(self, session: CaseSession) -> None:
        self.detail.show_session(session)
        self.stack.setCurrentWidget(self.detail)

    # ------------------------------------------------------------- pipeline
    def _run_pipeline(self) -> None:
        form = NewCaseDialog(self)
        if form.exec() != NewCaseDialog.Accepted:
            return
        name, operator, mount = form.values()

        self.dashboard.new_button.setEnabled(False)
        session = self._new_session(name, operator, mount)

        dialog = AnalysisDialog(self)
        thread = QThread(self)
        worker = AnalysisWorker(
            case=session.case, mount=mount, bridge=self.bridge, ai_backend=self.ai_backend
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.stage_started.connect(self._on_stage_started)
        worker.stage_ended.connect(self._on_stage_ended)
        worker.stage_started.connect(dialog.on_stage_start)
        worker.stage_ended.connect(dialog.on_stage_end)
        worker.message.connect(self._on_message)
        worker.message.connect(dialog.on_message)
        worker.finished.connect(dialog.finish)
        worker.failed.connect(dialog.set_error)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)

        self._thread = thread
        self._worker = worker
        self._session = session
        thread.start()
        dialog.exec()
        thread.quit()
        thread.wait(3000)
        self._thread = None
        self.dashboard.new_button.setEnabled(True)
        self.dashboard.set_sessions(self.sessions)

    def _on_message(self, msg: str, progress: int) -> None:
        if self._session is not None:
            self._session.logs.append(msg)

    def _on_stage_started(self, stage: str) -> None:
        if self._session is not None:
            self._session.stages[stage] = "running"

    def _on_stage_ended(self, stage: str, state: str) -> None:
        if self._session is not None:
            self._session.stages[stage] = "done" if state != "error" else "error"

    def _on_finished(self) -> None:
        if self._worker is None or self._worker.ctx is None or self._session is None:
            return
        ctx = self._worker.ctx
        anomalies = len(ctx.data.get("anomalies", []))
        self._session.finalize(
            ctx_files=ctx.files,
            results=self._worker.results,
            anomalies=anomalies,
        )
        self.dashboard.set_sessions(self.sessions)
        self._open_case(self._session)

    def _on_failed(self, message: str) -> None:
        if self._session is not None:
            self._session.status = "error"
            self._session.logs.append(f"[ERREUR] {message}")
        self.dashboard.set_sessions(self.sessions)

    # --------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
        super().closeEvent(event)