from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from insecured.models.evidence import EvidenceFile
from PySide6.QtGui import QColor


class EvidenceTable(QWidget):
    """Tableau des fichiers analysés (résultat de la pipeline)."""

    COLUMNS = ["Fichier", "Taille", "SHA-256", "Type détecté", "MIME", "VirusTotal", "Anomalie"]
    rowClicked = Signal(object)  # EvidenceFile

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.files: list[EvidenceFile] = []
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.cellClicked.connect(self._on_cell_clicked)
        head = QVBoxLayout(self)
        title = QLabel("Fichiers analysés")
        title.setStyleSheet("font-weight: bold;")
        head.addWidget(title)
        head.addWidget(self.table)

    def load(self, files: list[EvidenceFile]) -> None:
        self.files = files
        self.table.setRowCount(len(files))
        for row, f in enumerate(files):
            values = [
                f.path.as_posix(),
                self._size(f.size),
                f.sha256,
                f.magic,
                f.mime,
                f.vt,
                f.anom,
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col == len(self.COLUMNS) - 1 and f.anom:
                    item.setForeground(Qt.red)
                elif col == len(self.COLUMNS) - 2 and f.vt.startswith("⚠"):
                    item.setForeground(QColor("#f1c40f"))
                self.table.setItem(row, col, item)

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self.files):
            self.rowClicked.emit(self.files[row])

    @staticmethod
    def _size(n: int) -> str:
        if n >= 1 << 30:
            return f"{n / (1 << 30):.2f} Go"
        if n >= 1 << 20:
            return f"{n / (1 << 20):.1f} Mo"
        if n >= 1 << 10:
            return f"{n / (1 << 10):.0f} Ko"
        return f"{n} o"