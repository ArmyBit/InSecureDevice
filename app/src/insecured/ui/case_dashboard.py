from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from insecured.models.session import CaseSession
from insecured.ui.case_card import CaseCard


class OpsSummary(QFrame):
    """Chiffres globaux du dashboard : en cours / terminées / total (verre)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("opsBar")
        self.boxes: dict[str, tuple[QLabel, QLabel]] = {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        keys = ("running",)
        for key in keys + ("done", "total"):
            vbox = QVBoxLayout()
            v = QLabel("0")
            v.setObjectName("opsValue")
            c = QLabel(key)
            c.setObjectName("opsCaption")
            vbox.addWidget(v)
            vbox.addWidget(c)
            self.boxes[key] = (v, c)
            lay.addLayout(vbox, 1)

    def update_counts(self, running: int, done: int) -> None:
        self.boxes["running"][0].setText(str(running))
        self.boxes["done"][0].setText(str(done))
        self.boxes["total"][0].setText(str(running + done))
        self.boxes["running"][1].setText("Opérations en cours")
        self.boxes["done"][1].setText("Analyses terminées")
        self.boxes["total"][1].setText("Total analyses")


class CaseDashboard(QWidget):
    """Vue d'accueil (glassmorphism) : grille flex des cartes + nouvelle analyse."""

    newAnalysisRequested = Signal()
    cardClicked = Signal(object)  # CaseSession
    COLUMNS_PER_ROW = 9

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashRoot")

        title = QLabel("TABLEAU DE BORD")
        title.setObjectName("pageTitle")
        hint = QLabel("Sélectionnez une analyse ou lancez-en une nouvelle")
        hint.setObjectName("pageHint")
        self.new_button = QPushButton("＋  Nouvelle analyse")
        self.new_button.setCursor(Qt.PointingHandCursor)
        self.new_button.clicked.connect(self.newAnalysisRequested)
        head = QHBoxLayout()
        head.addWidget(title)
        head.addWidget(hint)
        head.addStretch(1)
        head.addWidget(self.new_button)

        self.summary = OpsSummary()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("dashScroll")
        self.grid_host = QWidget()
        self.grid_host.setObjectName("gridHost")
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 4, 0, 12)
        self.grid.setSpacing(14)
        for col in range(self.COLUMNS_PER_ROW):
            self.grid.setColumnStretch(col, 1)
        self.scroll.setWidget(self.grid_host)

        self.empty = QLabel("Aucune analyse lancée pour le moment.\nCliquez sur « ＋ Nouvelle analyse » pour commencer.")
        self.empty.setObjectName("emptyHint")
        self.empty.setAlignment(Qt.AlignCenter)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)
        lay.addLayout(head)
        lay.addWidget(self.summary)
        lay.addWidget(self.scroll, 1)
        self._apply_glass()

    def _apply_glass(self) -> None:
        self.setStyleSheet(
            """
            QWidget#dashRoot { background: transparent; }
            QLabel#pageTitle {
                color: #ffffff; font-size: 15px; font-weight: 800; letter-spacing: 2px;
            }
            QLabel#pageHint { color: rgba(255,255,255,0.45); font-size: 12px; }
            QFrame#opsBar {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.13);
                border-radius: 14px;
            }
            QLabel#opsValue { color: #fff; font-size: 20px; font-weight: 800; }
            QLabel#opsCaption { color: rgba(255,255,255,0.5); font-size: 10px; }
            QScrollArea#dashScroll, QWidget#gridHost { background: transparent; border: none; }
            QLabel#emptyHint {
                color: rgba(255,255,255,0.5); font-size: 14px; padding: 60px;
                background: rgba(255,255,255,0.04);
                border: 1px dashed rgba(255,255,255,0.18);
                border-radius: 18px;
            }
            """
        )

    def set_sessions(self, sessions: list[CaseSession]) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if not sessions:
            self.grid.addWidget(self.empty, 0, 0)
            self.summary.update_counts(0, 0)
            return
        running = sum(1 for s in sessions if s.is_running)
        done = sum(1 for s in sessions if not s.is_running)
        self.summary.update_counts(running, done)
        cols = self.COLUMNS_PER_ROW
        for i, session in enumerate(sessions):
            card = CaseCard(session)
            card.clicked.connect(self.cardClicked)
            self.grid.addWidget(card, i // cols, i % cols)