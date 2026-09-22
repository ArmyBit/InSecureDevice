from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QDialog, QWidget


def draw_backdrop(painter: QPainter, rect: QRectF) -> None:
    """Fond décoratif de verre : dégradé profond + halos colorés translucides."""
    painter.setRenderHint(QPainter.Antialiasing)
    base = QLinearGradient(rect.topLeft(), QRectF(rect).bottomRight())
    base.setColorAt(0.0, QColor("#0c0f16"))
    base.setColorAt(0.5, QColor("#111624"))
    base.setColorAt(1.0, QColor("#1a122a"))
    painter.fillRect(rect, base)
    blobs = (
        (0.06, 0.10, 0.45, QColor(61, 139, 253, 72)),
        (0.93, 0.04, 0.38, QColor(122, 92, 255, 60)),
        (0.86, 0.92, 0.42, QColor(46, 204, 113, 46)),
        (0.04, 0.94, 0.32, QColor(255, 196, 15, 30)),
    )
    w, h = rect.width(), rect.height()
    for fx, fy, radius, color in blobs:
        glow = QRadialGradient(w * fx, h * fy, w * radius)
        glow.setColorAt(0.0, color)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow)


class GlassWidget(QWidget):
    """Widget de fond : peint le décor de verre (halos) derrière le contenu."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        draw_backdrop(painter, QRectF(self.rect()))
        painter.end()


class GlassDialog(QDialog):
    """Dialog de verre : peint le fond décoratif translucide en arrière-plan."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        draw_backdrop(painter, QRectF(self.rect()))
        painter.end()


def glass_stylesheet() -> str:
    return f"""
    QWidget {{ color: #eaf0f8; font-size: 13px; font-family: 'Segoe UI'; }}
    QWidget#root, QMainWindow {{ background: transparent; }}
    QFrame#header {{
        background: rgba(255,255,255,0.05);
        border-bottom: 1px solid rgba(255,255,255,0.14);
    }}
    QLabel#appTitle {{ color: #fff; font-size: 19px; font-weight: 700; letter-spacing: 1px; }}
    QLabel#appSubtitle {{ color: rgba(255,255,255,0.5); font-size: 12px; }}
    QLabel#readyBadge {{ color: #2ecc71; font-size: 12px; font-weight: 600; }}
    QPushButton#winBtn {{
        background: rgba(255,255,255,0.05); border: none; border-radius: 6px;
        color: rgba(255,255,255,0.8); font-size: 14px; font-weight: 700;
    }}
    QPushButton#winBtn:hover {{ background: rgba(255,255,255,0.15); color: #fff; }}
    QPushButton#winClose {{
        background: transparent; border: none; border-radius: 6px;
        color: rgba(255,255,255,0.8); font-size: 14px; font-weight: 700;
    }}
    QPushButton#winClose:hover {{ background: #e74c3c; color: #fff; }}
    QLabel#pageTitle {{ color: rgba(255,255,255,0.85); font-size: 12px; font-weight: 800; letter-spacing: 2px; }}
    QLabel#detailTitle {{ color: #fff; font-size: 22px; font-weight: 700; }}
    QLabel#summary, QLabel#verdict {{ font-size: 14px; font-weight: 700; }}
    QLabel#detailInfo {{ color: rgba(255,255,255,0.5); font-size: 12px; }}
    QPushButton#reportButton {{
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.18); border-radius: 8px;
        padding: 8px 14px; color: #eaf0f8; font-weight: 600; font-size: 12px;
    }}
    QPushButton#reportButton:hover {{
        border-color: #8fa8ff; color: #fff;
        background: rgba(255,255,255,0.12);
    }}
    QPushButton#reportButton:disabled {{
        background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.35);
        border-color: rgba(255,255,255,0.08);
    }}
    QLabel#reportStatus {{ font-size: 12px; color: rgba(255,255,255,0.5); }}
    QFrame#card, QFrame#infoFrame, QFrame#opsBar {{
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.13);
        border-radius: 14px;
    }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{
        background: rgba(255,255,255,0.03); width: 10px; border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255,255,255,0.18); border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QPushButton#backButton {{
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 8px; padding: 8px 14px;
        color: rgba(255,255,255,0.8); font-weight: 600; font-size: 12px;
    }}
    QPushButton#backButton:hover {{ border-color: #8fa8ff; color: #fff; }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d8bfd, stop:1 #7a5cff);
        border: none; border-radius: 10px; padding: 10px 16px;
        color: #fff; font-weight: 700; font-size: 13px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #54a0ff, stop:1 #8f78ff);
    }}
    QPushButton:pressed {{ background: #7a5cff; }}
    QPushButton:disabled {{ background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.4); }}
    QTableWidget {{
        background: rgba(255,255,255,0.04);
        alternate-background-color: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.12); border-radius: 10px;
        gridline-color: rgba(255,255,255,0.07);
        font-size: 12px;
    }}
    QHeaderView::section {{
        background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.6);
        border: none; border-bottom: 1px solid rgba(255,255,255,0.10);
        padding: 6px; font-weight: 600;
    }}
    QTextEdit {{
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 10px; color: rgba(255,255,255,0.75);
        font-family: 'Consolas';
    }}
    QProgressBar {{
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12); border-radius: 7px;
        height: 12px; color: rgba(255,255,255,0.7);
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d8bfd, stop:1 #7a5cff);
        border-radius: 7px;
    }}
    QLineEdit {{
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 8px; padding: 6px 8px; color: #eaf0f8;
    }}
    QLineEdit:focus {{ border-color: #8fa8ff; }}
    """