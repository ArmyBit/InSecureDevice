from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from insecured.models.session import CaseSession

STATUS_META = {
    "running": ("● En cours", "#f1c40f"),
    "done": ("● Terminé", "#2ecc71"),
    "error": ("● Échec", "#e74c3c"),
}


class CaseCard(QFrame):
    """Carte verre (glassmorphism) d'une analyse. Cliquable, avec résumé."""

    clicked = Signal(object)  # CaseSession

    def __init__(self, session: CaseSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.setObjectName("caseCard")
        self.setCursor(Qt.PointingHandCursor)

        status_text, status_color = STATUS_META.get(session.status, STATUS_META["running"])
        self.badge = QLabel(status_text)
        self.badge.setObjectName("cardStatus")

        self.title = QLabel(session.case.name)
        self.title.setObjectName("cardTitle")
        self.title.setWordWrap(True)

        meta_fields = [session.case.case_id]
        if session.case.operator:
            meta_fields.append(f"op : {session.case.operator}")
        self.meta = QLabel(" · ".join(meta_fields))
        self.meta.setObjectName("cardMeta")
        self.meta.setWordWrap(True)

        self.mount = QLabel("💾  " + (session.mount_point or "—"))
        self.mount.setObjectName("cardMount")
        self.mount.setToolTip("Point de montage / ancrage de l'analyse")

        self.counts_labels: dict[str, QLabel] = {}
        counts_row = QHBoxLayout()
        counts_row.setSpacing(4)
        for key, label, color in (
            ("total", "Total", "#e6e8ec"),
            ("safe", "Sains", "#2ecc71"),
            ("suspect", "Suspects", "#e74c3c"),
        ):
            box = QVBoxLayout()
            box.setSpacing(0)
            value = QLabel("—")
            value.setObjectName("countValue")
            value.setStyleSheet(f"color: {color};")
            caption = QLabel(label)
            caption.setObjectName("countCaption")
            box.addWidget(value)
            box.addWidget(caption)
            self.counts_labels[key] = value
            counts_row.addLayout(box, 1)

        self.summary = QLabel("")
        self.summary.setObjectName("cardSummary")
        self.summary.setWordWrap(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(5)
        head = QHBoxLayout()
        head.setSpacing(6)
        head.addWidget(self.title, 1)
        head.addWidget(self.badge, 0, Qt.AlignTop)
        lay.addLayout(head)
        lay.addWidget(self.meta)
        lay.addWidget(self.mount)
        lay.addStretch(1)
        lay.addLayout(counts_row)
        lay.addWidget(self.summary)

        accent = "#f1c40f" if session.is_running else ("#e74c3c" if session.status == "error" else "#3d8bfd")
        self._style(accent)
        self.refresh()

    def _style(self, accent: str) -> None:
        self.setStyleSheet(
            f"""
            QFrame#caseCard {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-top: 2px solid {accent};
                border-radius: 14px;
            }}
            QFrame#caseCard:hover {{
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.30);
                border-top: 2px solid #ffffff;
            }}
            QLabel {{ background: transparent; }}
            QLabel#cardTitle {{ color: #ffffff; font-size: 13px; font-weight: 700; }}
            QLabel#cardMeta {{ color: rgba(255,255,255,0.45); font-size: 10px; }}
            QLabel#cardMount {{ color: rgba(255,255,255,0.7); font-size: 11px; }}
            QLabel#cardStatus {{ color: #2ecc71; font-size: 10px; font-weight: 700; }}
            QLabel#countCaption {{ color: rgba(255,255,255,0.4); font-size: 9px; }}
            QLabel#cardSummary {{
                color: rgba(255,255,255,0.75); font-size: 10px;
                border-top: 1px solid rgba(255,255,255,0.12);
                padding-top: 6px;
            }}
            """
        )

    def refresh(self) -> None:
        total, safe, suspects = self.session.counts
        marks = {"running": "●", "done": "✓", "error": "✕"}
        self.badge.setText(f"{marks.get(self.session.status, '●')} {STATUS_META.get(self.session.status, STATUS_META['running'])[0]}")
        self.counts_labels["total"].setText(str(total))
        self.counts_labels["safe"].setText(str(safe))
        self.counts_labels["suspect"].setText(str(suspects))
        if self.session.is_running:
            self.summary.setText("Analyse en cours…")
        elif self.session.status == "error":
            self.summary.setText("Échec — aucun résultat exploitable")
        else:
            self.summary.setText(
                f"{safe} sains / {suspects} suspects · {self.session.anomalies} anomalie(s)"
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.session)
        super().mousePressEvent(event)