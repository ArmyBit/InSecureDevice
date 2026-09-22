from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget, QLabel, QFrame, QVBoxLayout


class StatCard(QFrame):
    """Carte KPI : titre + grande valeur chiffrée."""

    ACCENTS = {
        "total": "#3d8bfd",
        "safe": "#2ecc71",
        "suspect": "#e74c3c",
        "anomalies": "#f39c12",
    }

    def __init__(self, title: str, key: str, value: str = "0") -> None:
        super().__init__()
        self.setObjectName("statCard")
        self.key = key
        self.title = QLabel(title)
        self.title.setObjectName("statTitle")
        self.value = QLabel(value)
        self.value.setObjectName("statValue")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        lay.addWidget(self.title)
        lay.addWidget(self.value)

    def set_value(self, value) -> None:
        self.value.setText(str(value))

    def apply_style(self) -> None:
        accent = self.ACCENTS.get(self.key, "#3d8bfd")
        self.setStyleSheet(
            f"""
            QFrame#statCard {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.12);
                border-left: 4px solid {accent};
                border-radius: 12px;
            }}
            QLabel#statTitle {{ color: rgba(255,255,255,0.55); font-size: 12px; }}
            QLabel#statValue {{ color: {accent}; font-size: 28px; font-weight: 700; }}
            """
        )


class StatsView(QWidget):
    """Rangée de cartes KPI : totaux, fichiers sains, suspects, anomalies."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cards = {
            "total": StatCard("Fichiers analysés", "total"),
            "safe": StatCard("Fichiers sains", "safe"),
            "suspect": StatCard("Fichiers suspects", "suspect"),
            "anomalies": StatCard("Anomalies", "anomalies"),
        }
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        for card in self.cards.values():
            card.apply_style()
            lay.addWidget(card, 1)

    def reset(self) -> None:
        for card in self.cards.values():
            card.set_value("0")

    def update_counts(self, total: int, safe: int, suspicious: int, anomalies: int) -> None:
        self.cards["total"].set_value(total)
        self.cards["safe"].set_value(safe)
        self.cards["suspect"].set_value(suspicious)
        self.cards["anomalies"].set_value(anomalies)