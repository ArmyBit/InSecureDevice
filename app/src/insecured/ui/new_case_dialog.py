from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from insecured.ui.theme import GlassDialog, glass_stylesheet


class NewCaseDialog(GlassDialog):
    """Petit formulaire de verre d'ouverture d'une analyse (nom, opérateur, montage)."""

    def __init__(self, parent=None, default_mount: str = "DEV_MEDIA") -> None:
        super().__init__(parent)
        self.setWindowTitle("Nouvelle analyse")
        self.setMinimumWidth(420)

        title = QLabel("Nouvelle analyse")
        title.setObjectName("dlgTitle")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ex. CAS-2026-001")
        self.operator_edit = QLineEdit()
        self.operator_edit.setPlaceholderText("nom de l'opérateur")
        self.mount_edit = QLineEdit(default_mount)
        self.mount_edit.setPlaceholderText("point de montage de l'image (lecture seule)")

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow("Cas", self.name_edit)
        form.addRow("Opérateur", self.operator_edit)
        form.addRow("Montage", self.mount_edit)

        self.run_button = QPushButton("Lancer l'analyse")
        self.run_button.setObjectName("runButton")
        self.run_button.clicked.connect(self.accept)

        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.addWidget(title)
        lay.addLayout(form)
        lay.addWidget(self.run_button)
        lay.addWidget(cancel)

        self.setStyleSheet(
            glass_stylesheet()
            + """
            GlassDialog { background: transparent; }
            QLabel { color: #eaf0f8; font-size: 13px; }
            QLabel#dlgTitle { color: #fff; font-size: 17px; font-weight: 700; }
            QPushButton#runButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d8bfd, stop:1 #7a5cff);
            }
            """
        )

    def values(self) -> tuple[str, str, str]:
        name = self.name_edit.text().strip() or "cas-rapide"
        return name, self.operator_edit.text().strip(), self.mount_edit.text().strip() or "DEV_MEDIA"