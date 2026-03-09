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
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsRectItem, QSizePolicy,
    QWidget, QHBoxLayout, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, QPoint
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

INNER_COLS = 4
INNER_ROWS = 4

EVEN_INNER_COLS = 2
EVEN_INNER_ROWS = 2

CELL_SIZE = 36

OUTER_LINE_WIDTH      = 3.0
INNER_LINE_WIDTH      = 1.5
EVEN_INNER_LINE_WIDTH = 0.6

LINE_COLOR       = QColor("#2c2c2c")
DOT_COLOR        = QColor("#00c8fa")
DOT_RADIUS       = 8
BACKGROUND_COLOR = QColor("#cfcfcf")
HOVER_RECT_COLOR = QColor("#00c8fa")

PADDING = 50

# ── Derived geometry ──────────────────────────────────────────────────────────

CELL_W = EVEN_INNER_COLS * CELL_SIZE
CELL_H = EVEN_INNER_ROWS * CELL_SIZE

INNER_W = INNER_COLS * CELL_W
INNER_H = INNER_ROWS * CELL_H

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


# ── Hoverable List Widget ─────────────────────────────────────────────────────

class HoverListWidget(QListWidget):
    """A QListWidget that emits item_hovered(item) as the mouse moves over rows,
    and item_unhovered() when the mouse leaves the widget entirely."""

    item_hovered   = Signal(QListWidgetItem)
    item_unhovered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._last_hovered = None

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item and item is not self._last_hovered:
            self._last_hovered = item
            self.item_hovered.emit(item)
        elif not item and self._last_hovered is not None:
            self._last_hovered = None
            self.item_unhovered.emit()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._last_hovered is not None:
            self._last_hovered = None
            self.item_unhovered.emit()
        super().leaveEvent(event)


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

    # Level 3: even-inner lines
    for ogy in range(OUTER_ROWS):
        for ogx in range(OUTER_COLS):
            for iy in range(INNER_ROWS):
                for ix in range(INNER_COLS):
                    ox = ogx * INNER_W + ix * CELL_W
                    oy = ogy * INNER_H + iy * CELL_H
                    for ex in range(EVEN_INNER_COLS + 1):
                        x = ox + ex * CELL_SIZE
                        scene.addLine(x, oy, x, oy + CELL_H, even_inner_pen).setZValue(1)
                    for ey in range(EVEN_INNER_ROWS + 1):
                        y = oy + ey * CELL_SIZE
                        scene.addLine(ox, y, ox + CELL_W, y, even_inner_pen).setZValue(1)

    # Level 2: inner lines
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

    # Level 1: outer lines
    for ogx in range(OUTER_COLS + 1):
        x = ogx * INNER_W
        scene.addLine(x, 0, x, TOTAL_H, outer_pen).setZValue(3)
    for ogy in range(OUTER_ROWS + 1):
        y = ogy * INNER_H
        scene.addLine(0, y, TOTAL_W, y, outer_pen).setZValue(3)

    # Clickable dots
    seen: set = set()

    def add_dot(cx, cy):
        key = (cx, cy)
        if key not in seen:
            seen.add(key)
            scene.addItem(IntersectionDot(cx, cy, on_toggle=on_dot_toggle))

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
        self._hover_rect: QGraphicsRectItem | None = None

        self._scene = build_scene(on_dot_toggle=self._on_dot_toggle)
        self._view  = GridView(self._scene)

        # --- List panel -------------------------------------------------------
        self._list = HoverListWidget()
        self._list.setFixedWidth(220)
        self._list.setStyleSheet("""
            QListWidget {
                background: #cfcfcf;
                color: #1e1e1e;
                font-family: monospace;
                font-size: 12px;
                border-left: 1px solid darkgray;
                padding: 4px;
                outline: 0;
            }
            QListWidget::item {
                padding: 6px 4px;
                border-bottom: 1px solid #b0b0b0;
            }
            QListWidget::item:hover {
                background: #b8eaf7;
            }
            QListWidget::item:selected {
                background: #80d8f0;
                color: #1e1e1e;
            }
        """)
        self._list.setWordWrap(True)
        self._list.setTextElideMode(Qt.TextElideMode.ElideNone)

        self._list.item_hovered.connect(self._on_item_hover)
        self._list.item_unhovered.connect(self._clear_hover_rect)

        # --- Layout -----------------------------------------------------------
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._view)
        layout.addWidget(self._list)
        self.setCentralWidget(container)

        self.resize(
            min(TOTAL_W + 2 * PADDING + 40 + 220, 1400),
            min(TOTAL_H + 2 * PADDING + 80, 900),
        )

    # ── Dot toggle → populate list ────────────────────────────────────────────

    def _on_dot_toggle(self, cx, cy, active):
        if active:
            gx = cx // CELL_SIZE
            gy = cy // CELL_SIZE
            paragraphs = CONTENT.get((gx, gy), [])
            for paragraph in paragraphs:
                item = QListWidgetItem(paragraph)
                # Store the dot coords so we can look up the inner cell later
                item.setData(Qt.ItemDataRole.UserRole, (cx, cy))
                self._list.addItem(item)
        else:
            # Remove all items that belong to this dot
            for i in range(self._list.count() - 1, -1, -1):
                item = self._list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == (cx, cy):
                    self._list.takeItem(i)
        self._clear_hover_rect()

    # ── Hover → draw inner-cell rectangle ────────────────────────────────────
# HELLO WORLD
    def _inner_cell_rect(self, cx: int, cy: int):
        """Return (x, y, w, h) of the inner cell that contains pixel (cx, cy)."""
        # Which inner cell column/row does this dot sit in?
        inner_col = cx // CELL_W
        inner_row = cy // CELL_H
        rx = inner_col * CELL_W
        ry = inner_row * CELL_H
        return rx, ry, CELL_W, CELL_H

    def _on_item_hover(self, item: QListWidgetItem):
        self._clear_hover_rect()
        coords = item.data(Qt.ItemDataRole.UserRole)
        if coords is None:
            return
        cx, cy = coords
        rx, ry, rw, rh = self._inner_cell_rect(cx, cy)

        rect_pen = QPen(HOVER_RECT_COLOR, 2.5, Qt.PenStyle.SolidLine)
        fill = QColor(HOVER_RECT_COLOR)
        fill.setAlpha(35)

        rect_item = QGraphicsRectItem(rx, ry, rw, rh)
        rect_item.setPen(rect_pen)
        rect_item.setBrush(QBrush(fill))
        rect_item.setZValue(5)
        self._scene.addItem(rect_item)
        self._hover_rect = rect_item

    def _clear_hover_rect(self):
        if self._hover_rect is not None:
            self._scene.removeItem(self._hover_rect)
            self._hover_rect = None

    # ── Fit on show ──────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._view.fitInView(
            self._scene.sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Grid of Grids")
    win = GridWindow()
    win.show()
    sys.exit(app.exec())