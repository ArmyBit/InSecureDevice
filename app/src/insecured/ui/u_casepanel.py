from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CasePanel(QWidget):
    """Formulaire d'ouverture d'un cas et pilotage de la pipeline."""

    runRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        form = QGroupBox("Cas")
        lay = QFormLayout(form)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ex. CAS-2026-001")
        self.operator_edit = QLineEdit()
        self.mount_edit = QLineEdit("DEV_MEDIA")
        self.mount_edit.setPlaceholderText("Point de montage image (lecture seule)")
        lay.addRow("Nom du cas", self.name_edit)
        lay.addRow("Opérateur", self.operator_edit)
        lay.addRow("Montage", self.mount_edit)

        self.run_button = QPushButton("Lancer l'analyse")
        self.run_button.clicked.connect(self.runRequested)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status = QLabel("Prêt")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        box = QVBoxLayout(self)
        box.addWidget(form)
        box.addWidget(self.run_button)
        box.addWidget(self.progress)
        box.addWidget(self.status)
        box.addWidget(QLabel("Journal des étapes"))
        box.addWidget(self.log)

    def append_log(self, text: str) -> None:
        self.log.append(text)

    def set_progress(self, value: int) -> None:
        self.progress.setValue(value)

    def set_status(self, text: str) -> None:
        self.status.setText(text)