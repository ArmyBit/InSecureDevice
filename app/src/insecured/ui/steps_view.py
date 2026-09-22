from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QFrame, QHBoxLayout

STEP_ORDER = [
    "mount",
    "inventory",
    "hashing",
    "metadata",
    "anomalies",
    "vt_check",
    "ai_analysis",
    "report",
]


class StepRow(QFrame):
    """Une étape du stepper vertical : pastille d'état + libellé."""

    STATES = {
        "pending": ("●", "#3a4152", "Étapes à venir"),  # gris
        "running": ("◉", "#f1c40f", "En cours"),        # orange
        "done": ("●", "#2ecc71", "Terminé"),            # vert
        "skip": ("○", "#7f8fa6", "Ignoré"),             # gris clair
        "error": ("●", "#e74c3c", "Échec"),             # rouge
    }

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stepRow")
        self.dot = QLabel("●")
        self.label = QLabel(label)
        self.state = QLabel()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)
        lay.addWidget(self.dot, 0, Qt.AlignCenter)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.state, 0, Qt.AlignRight)
        self.set_state("pending")

    def set_state(self, state: str) -> None:
        if state not in self.STATES:
            state = "pending"
        symbol, color, text = self.STATES[state]
        self.dot.setText(symbol)
        self.state.setText(text)
        self.setStyleSheet(
            f"""
            QFrame#stepRow {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.12);
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
            QLabel {{ color: #eaf0f8; font-size: 13px; }}
            #dot {{ color: {color}; font-size: 16px; }}
            """
        )


class StepsView(QWidget):
    """Stepper vertical : affiche le déroulé des étapes du process."""

    STEP_LABELS = [
        "Montage du support",
        "Inventaire des fichiers",
        "Analyse statique (hash)",
        "Métadonnées & signatures",
        "Détection d'anomalies",
        "Vérification VirusTotal",
        "Analyse IA (reverse)",
        "Rapport",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("ÉTAPES DU PROCESS")
        title.setObjectName("panelTitle")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(title)
        self.rows: list[StepRow] = []
        for label in self.STEP_LABELS:
            row = StepRow(label)
            self.rows.append(row)
            lay.addWidget(row)
        lay.addStretch(1)

    def reset(self) -> None:
        for row in self.rows:
            row.set_state("pending")

    def set_state(self, index: int, state: str) -> None:
        if 0 <= index < len(self.rows):
            self.rows[index].set_state(state)