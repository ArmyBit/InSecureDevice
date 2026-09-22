from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QPushButton,
    QFrame,
    QVBoxLayout,
)

from insecured.models.evidence import EvidenceFile
from insecured.ui.theme import GlassDialog, glass_stylesheet


class FileInfoDialog(GlassDialog):
    """Dialog de verre : détail d'un fichier analysé (au clic sur une ligne)."""

    def __init__(self, f: EvidenceFile, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Détail du fichier")
        self.setMinimumWidth(520)

        title = QLabel(f.path.name)
        title.setObjectName("fileTitle")

        verdict = QLabel(self._verdict_text(f))
        verdict.setObjectName("fileVerdict")

        frame = QFrame()
        frame.setObjectName("infoFrame")
        form = QFormLayout(frame)
        form.setSpacing(8)
        form.addRow("Chemin", QLabel(f.path.as_posix()))
        form.addRow("Taille", QLabel(self._size(f.size)))
        form.addRow("SHA-256", QLabel(f.sha256 or "—"))
        form.addRow("Type détecté", QLabel(f.magic or "—"))
        form.addRow("MIME", QLabel(f.mime or "—"))
        form.addRow("Modifié le", QLabel(self._dt(f.modified)))
        form.addRow("Créé le", QLabel(self._dt(f.created)))
        form.addRow("Anomalie", QLabel(f.anom or "aucune"))
        vt = QLabel(f.vt or "non vérifié")
        if f.vt.startswith("⚠"):
            vt.setStyleSheet("color: #f1c40f; font-weight: 600;")
        elif f.vt.startswith("✓"):
            vt.setStyleSheet("color: #2ecc71; font-weight: 600;")
        form.addRow("VirusTotal", vt)
        notes = QLabel(f.notes or "—")
        notes.setWordWrap(True)
        form.addRow("Notes IA", notes)

        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(title)
        lay.addWidget(verdict)
        lay.addWidget(frame)
        lay.addWidget(ok)

        clean = not f.is_suspicious
        color = "#2ecc71" if clean else "#e74c3c"
        self.setStyleSheet(
            glass_stylesheet()
            + f"""
            GlassDialog {{ background: transparent; }}
            QLabel {{ color: #eaf0f8; font-size: 13px; }}
            QLabel#fileTitle {{ color: #fff; font-size: 18px; font-weight: 700; }}
            QLabel#fileVerdict {{ color: {color}; font-weight: 700; font-size: 14px; }}
            QFrame#infoFrame {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.13); border-radius: 12px;
            }}
            """
        )

    @staticmethod
    def _dt(value) -> str:
        if not value:
            return "—"
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _size(n: int) -> str:
        if n >= 1 << 30:
            return f"{n / (1 << 30):.2f} Go"
        if n >= 1 << 20:
            return f"{n / (1 << 20):.1f} Mo"
        if n >= 1 << 10:
            return f"{n / (1 << 10):.0f} Ko"
        return f"{n} o"

    @staticmethod
    def _verdict_text(f: EvidenceFile) -> str:
        if f.is_suspicious:
            return "⚠ FICHIER SUSPECT"
        return "✓ Fichier sain"