"""
Grid of Grids — PySide6  (3-level hierarchy)
============================================
Level 1: Outer grid       — thick lines
Level 2: Inner sub-grids  — medium lines
Level 3: Even-inner cells — thin lines

All intersections at every level are clickable to toggle dots.
Middle-mouse drag to pan. Scroll wheel to zoom.

Requirements:  pip install PySide6
Usage:         python grid_of_grids.py
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView,
    QGraphicsScene, QGraphicsEllipseItem, QSizePolicy,
    QWidget, QHBoxLayout, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor, QBrush, QPainter, QIcon
import json

with open("config.json") as f:
    raw = json.load(f)

CONTENT = {
    tuple(int(v) for v in key.split(",")): paragraphs
    for key, paragraphs in raw.items()
}
# ── Configuration ─────────────────────────────────────────────────────────────

OUTER_COLS = 2
OUTER_ROWS = 2

INNER_COLS = 4          # sub-grid divisions per outer cell
INNER_ROWS = 4

EVEN_INNER_COLS = 2     # smallest cell divisions per inner cell
EVEN_INNER_ROWS = 2

CELL_SIZE = 36          # pixels between adjacent even-inner intersections

OUTER_LINE_WIDTH    = 3.0
INNER_LINE_WIDTH    = 1.5
EVEN_INNER_LINE_WIDTH = 0.6

LINE_COLOR       = QColor("#2c2c2c")
DOT_COLOR        = QColor("#00c8fa")
DOT_RADIUS       = 8
BACKGROUND_COLOR = QColor("#cfcfcf")

PADDING = 50

# ── Derived geometry ──────────────────────────────────────────────────────────

# size of the smallest cell (even-inner)
CELL_W = EVEN_INNER_COLS * CELL_SIZE
CELL_H = EVEN_INNER_ROWS * CELL_SIZE

# size of one inner sub-grid block
INNER_W = INNER_COLS * CELL_W
INNER_H = INNER_ROWS * CELL_H

# total canvas size
TOTAL_W = OUTER_COLS * INNER_W
TOTAL_H = OUTER_ROWS * INNER_H


# ── Clickable intersection dot ────────────────────────────────────────────────

class IntersectionDot(QGraphicsEllipseItem):
    def __init__(self, cx, cy, radius=DOT_RADIUS, on_toggle=None):
        r = radius
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.setPos(cx, cy)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._active = False
        self._cx = cx
        self._cy = cy
        self._on_toggle = on_toggle
        self._apply_style()

    def _apply_style(self):
        if self._active:
            self.setBrush(QBrush(DOT_COLOR))
            self.setPen(QPen(DOT_COLOR.darker(140), 1))
        else:
            self.setBrush(QBrush(Qt.GlobalColor.transparent))
            self.setPen(QPen(Qt.GlobalColor.transparent))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._active = not self._active
            if self._on_toggle:
                self._on_toggle(self._cx, self._cy, self._active)
            self._apply_style()
            event.accept()
        else:
            super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        if not self._active:
            self.setBrush(QBrush(DOT_COLOR.lighter(170)))
            self.setPen(QPen(DOT_COLOR, 1.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._apply_style()
        super().hoverLeaveEvent(event)


# ── Scene builder ─────────────────────────────────────────────────────────────

def build_scene(on_dot_toggle=None) -> QGraphicsScene:
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(BACKGROUND_COLOR))

    def pen(width):
        return QPen(LINE_COLOR, width, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.FlatCap, Qt.PenJoinStyle.MiterJoin)

    outer_pen      = pen(OUTER_LINE_WIDTH)
    inner_pen      = pen(INNER_LINE_WIDTH)
    even_inner_pen = pen(EVEN_INNER_LINE_WIDTH)

    # ── Level 3: even-inner lines (thinnest) ─────────────────────────────────
    # Iterate every inner cell and draw EVEN_INNER subdivisions inside it
    for ogy in range(OUTER_ROWS):
        for ogx in range(OUTER_COLS):
            for iy in range(INNER_ROWS):
                for ix in range(INNER_COLS):
                    # origin of this inner cell
                    ox = ogx * INNER_W + ix * CELL_W
                    oy = ogy * INNER_H + iy * CELL_H
                    # vertical lines
                    for ex in range(EVEN_INNER_COLS + 1):
                        x = ox + ex * CELL_SIZE
                        scene.addLine(x, oy, x, oy + CELL_H, even_inner_pen).setZValue(1)
                    # horizontal lines
                    for ey in range(EVEN_INNER_ROWS + 1):
                        y = oy + ey * CELL_SIZE
                        scene.addLine(ox, y, ox + CELL_W, y, even_inner_pen).setZValue(1)

    # ── Level 2: inner lines (medium) ────────────────────────────────────────
    for ogy in range(OUTER_ROWS):
        for ogx in range(OUTER_COLS):
            ox = ogx * INNER_W
            oy = ogy * INNER_H
            for ix in range(INNER_COLS + 1):
                x = ox + ix * CELL_W
                scene.addLine(x, oy, x, oy + INNER_H, inner_pen).setZValue(2)
            for iy in range(INNER_ROWS + 1):
                y = oy + iy * CELL_H
                scene.addLine(ox, y, ox + INNER_W, y, inner_pen).setZValue(2)

    # ── Level 1: outer lines (thickest, on top) ───────────────────────────────
    for ogx in range(OUTER_COLS + 1):
        x = ogx * INNER_W
        scene.addLine(x, 0, x, TOTAL_H, outer_pen).setZValue(3)
    for ogy in range(OUTER_ROWS + 1):
        y = ogy * INNER_H
        scene.addLine(0, y, TOTAL_W, y, outer_pen).setZValue(3)

    # ── Clickable dots at every intersection ──────────────────────────────────
    seen: set = set()

    def add_dot(cx, cy):
        key = (cx, cy)
        if key not in seen:
            seen.add(key)
            scene.addItem(IntersectionDot(cx, cy, on_toggle=on_dot_toggle))

    # even-inner intersections (every CELL_SIZE step)
    for ogy in range(OUTER_ROWS):
        for ogx in range(OUTER_COLS):
            for iy in range(INNER_ROWS):
                for ix in range(INNER_COLS):
                    ox = ogx * INNER_W + ix * CELL_W
                    oy = ogy * INNER_H + iy * CELL_H
                    for ey in range(EVEN_INNER_ROWS + 1):
                        for ex in range(EVEN_INNER_COLS + 1):
                            add_dot(ox + ex * CELL_SIZE, oy + ey * CELL_SIZE)

    scene.setSceneRect(-PADDING, -PADDING,
                       TOTAL_W + 2 * PADDING,
                       TOTAL_H + 2 * PADDING)
    return scene


# ── Custom view ───────────────────────────────────────────────────────────────

class GridView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background: {BACKGROUND_COLOR.name()}; border: none;")
        self._pan_last = None

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_last is not None:
            delta = event.position() - self._pan_last
            self._pan_last = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)


# ── Main window ───────────────────────────────────────────────────────────────

class GridWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AtlasAstro Innovations | Section Corner Reference")
        self.setWindowIcon(QIcon("AtlasIcon.ico"))
        self._scene = build_scene(on_dot_toggle=self._on_dot_toggle)
        self._view = GridView(self._scene)
        self.resize(
            min(TOTAL_W + 2 * PADDING + 40, 1200),
            min(TOTAL_H + 2 * PADDING + 80, 900),
        )
        # --- Text Panel -------------------------------------------------------
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFixedWidth(220)
        self._text.setStyleSheet("""
            QTextEdit {
                background: #cfcfcf;
                color: #1e1e1e;
                font-family: monospace;
                font-size: 12px;
                border-left-width: 1px;
                border-left-color: darkgray;
                border-left-style: solid;
                padding: 8px;                     
            }                         
        """)
        self._text.setPlainText("No intersection selected.")

        # --- Layout -----------------------------------------------------------
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._view)
        layout.addWidget(self._text)
        self.setCentralWidget(container)

        self.resize(
            min(TOTAL_W + 2 * PADDING + 40 + 220, 1400),
            min(TOTAL_H + 2 * PADDING + 80, 900),
        )

    def _on_dot_toggle(self, cx, cy, active):
        if active:
            gx = cx // CELL_SIZE
            gy = cy // CELL_SIZE
            for paragraph in CONTENT[gx, gy]:
                self._text.append(f"{paragraph}\n")
        else:
            self._text.clear()

    def log(self, message: str):
        """Append a line to the text panel"""
        self._text.append(message)

    def showEvent(self, event):
        super().showEvent(event)
        self._view.fitInView(
            self._scene.sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("AtlasAstro Innovations | Section Corner Reference")
    win = GridWindow()
    win.show()
    sys.exit(app.exec())