# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

# Disclaimer: this script is inspired by
# https://github.com/marcel-goldschen-ohm/PyQtImageViewer

import os.path

try:
    from PyQt6.QtCore import Qt, QRectF, QPoint, QPointF, pyqtSignal, QEvent, QSize
    from PyQt6.QtGui import QImage, QPixmap, QPainterPath, QMouseEvent, QPainter, QPen, QBrush, QColor, QKeyEvent
    from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QSizePolicy, QGraphicsItem, QGraphicsRectItem, QPushButton, QGraphicsProxyWidget
except ImportError:
    try:
        from PyQt5.QtCore import Qt, QRectF, QPoint, QPointF, pyqtSignal, QEvent, QSize
        from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QMouseEvent, QPainter, QPen, QBrush, QColor, QKeyEvent
        from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QSizePolicy, QGraphicsItem, QGraphicsRectItem, QPushButton, QGraphicsProxyWidget
    except ImportError:
        raise ImportError("Requires PyQt (version 5 or 6)")


class QtImageViewer(QGraphicsView):
    def __init__(self, img, enable_select=False, parent=None):
        QGraphicsView.__init__(self, parent)

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._zoom_factor = 1.10
        self.aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio

        # Scroll bar behaviour.
        #   Qt.ScrollBarAlwaysOff: Never shows a scroll bar.
        #   Qt.ScrollBarAlwaysOn: Always shows a scroll bar.
        #   Qt.ScrollBarAsNeeded: Shows a scroll bar only when zoomed.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Interactions (set buttons to None to disable interactions)
        # !!! Events handled by interactions will NOT emit *MouseButton* signals.
        #     Note: regionSelectionButton will still emit a *MouseButtonReleased signal on a click (i.e. tiny box).
        self.regionSelectionButton = Qt.MouseButton.LeftButton  # Drag a zoom box.
        self.panButton = Qt.MouseButton.RightButton  # Drag to pan.
        self.wheelZoomFactor = 1.1  # Set to None or 1 to disable mouse wheel zoom.

        # Stack of QRectF zoom boxes in scene coordinates.
        # !!! If you update this manually, be sure to call updateViewer() to reflect any changes.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Displayed image pixmap in the QGraphicsScene.
        self._image = self.scene.addPixmap(img)
        self.setSceneRect(QRectF(img.rect()))  # Set scene size to image size.

        # selected predefined field
        self.selected_field = None
        # free form select
        self.enable_select = enable_select
        if enable_select:
            self._selection_rect = ResizableRectItem(0,0,0,0)
            self.scene.addItem(self._selection_rect)
        self.selection_rect = None
        self.fitInView(self.sceneRect(), self.aspectRatioMode)
        self.scale(2.0,2.0)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.isAccepted():
            return

        # Start dragging a region zoom box?
        if self.enable_select and (self.regionSelectionButton is not None) and (event.button() == self.regionSelectionButton):
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            super().mousePressEvent(event)
            event.accept()
            return

        # Start dragging to pan?
        if (self.panButton is not None) and (event.button() == self.panButton):
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if self.panButton == Qt.MouseButton.LeftButton:
                super().mousePressEvent(event)
            else:
                # ScrollHandDrag ONLY works with LeftButton, so fake it.
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                dummyEvent = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(event.pos()), Qt.MouseButton.LeftButton, event.buttons(), event.modifiers())
                super().mousePressEvent(dummyEvent)
            event.accept()
            return

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.isAccepted():
            return

        # Finish dragging a region zoom box?
        if self.enable_select and (self.regionSelectionButton is not None) and (event.button() == self.regionSelectionButton):
            # QGraphicsView.mouseReleaseEvent(self, event)
            rect = self.scene.selectionArea().boundingRect().intersected(self.sceneRect())
            # todo if selection too small (single click) -> take minimum size
            self._selection_rect.setRect(rect)
            self._selection_rect.setPos(0,0)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            event.accept()
            return

        # Finish panning?
        if (self.panButton is not None) and (event.button() == self.panButton):
            if not self.panButton == Qt.MouseButton.LeftButton:
                # ScrollHandDrag ONLY works with LeftButton, so fake it.
                if self.enable_select:
                    self.setCursor(Qt.CursorShape.CrossCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                dummyEvent = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(event.pos()), Qt.MouseButton.LeftButton, event.buttons(), event.modifiers())
                super().mouseReleaseEvent(dummyEvent)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            event.accept()
            return

    def wheelEvent(self, event):
        if self.wheelZoomFactor is not None and (Qt.KeyboardModifier.ControlModifier in event.modifiers()):
            if self.wheelZoomFactor == 1:
                return

            if event.angleDelta().y() > 0:
                zoom_factor = self._zoom_factor
            else:
                zoom_factor = 1 / self._zoom_factor
            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if event.isAccepted():
            return

    def enterEvent(self, event):
        if self.enable_select:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def addRect(self, name, x, y, width, height):
        rect = ClickableRectItem(name, x, y, width, height, onclick=self.selectField)
        # self.scene.addItem(rect)
        btn = self.scene.addWidget(rect)
        btn.setPos(x, y)

    def selectField(self, name):
        self.selected_field = name
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.isAutoRepeat():
            event.accept()
            return

        if self.enable_select and event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            rect = self._selection_rect.mapToScene(self._selection_rect.rect()).boundingRect()
            self.selection_rect = { 'x': rect.x(), 'y': rect.y(), 'width': rect.width(), 'height': rect.height() }
            self.close()
        else:
            super().keyPressEvent(event)


class ClickableRectItem(QPushButton):
    def __init__(self, name, x, y, w, h, parent=None, onclick=lambda x: ()):
        super().__init__()
        self.resize(int(w),int(h))
        self.setText(str(name))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 120, 215, 20);
                border: 2px solid #0078d7;
                color: #0078d7;
                text-size: 2em;
                font-size: {int(h*0.7)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 120, 215, 40);
            }}
        """)
        self._name = name
        self._onclick = onclick
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._onclick(self._name)
        else:
            # Otherwise, default movable/selectable behavior
            super().mousePressEvent(event)

class ResizableRectItem(QGraphicsRectItem):
    EDGE_MARGIN = 10  # how close to the edge to count as a "resize zone" TODO make dependent on zoom level

    def __init__(self, x, y, w, h, parent=None):
        super().__init__(0, 0, w, h, parent)
        self.setPos(x,y)
        self.setFlags(
            self.GraphicsItemFlag.ItemIsMovable
        )
        self.setAcceptHoverEvents(True)
        pen = QPen(QColor(0,120,215), 2)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(0, 120, 215, 40)))

        self._resizing = False
        self._resize_edge = None
        self._start_rect = None
        self._start_pos = None

    def hoverMoveEvent(self, event):
        """Change the cursor when hovering near an edge."""
        pos = event.pos()
        rect = self.rect()
        margin = self.EDGE_MARGIN
        on_left   = abs(pos.x() - rect.left()) < margin
        on_right  = abs(pos.x() - rect.right()) < margin
        on_top    = abs(pos.y() - rect.top()) < margin
        on_bottom = abs(pos.y() - rect.bottom()) < margin

        # Determine which edge/corner we’re on
        if on_left and on_top:
            self._resize_edge = "top_left"
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif on_right and on_top:
            self._resize_edge = "top_right"
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif on_left and on_bottom:
            self._resize_edge = "bottom_left"
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif on_right and on_bottom:
            self._resize_edge = "bottom_right"
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif on_left:
            self._resize_edge = "left"
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif on_right:
            self._resize_edge = "right"
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif on_top:
            self._resize_edge = "top"
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif on_bottom:
            self._resize_edge = "bottom"
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self._resize_edge = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()


        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Right-click: pick nearest corner regardless of distance
            rect = self.rect()
            pos = event.pos()

            corners = {
                "top_left": rect.topLeft(),
                "top_right": rect.topRight(),
                "bottom_left": rect.bottomLeft(),
                "bottom_right": rect.bottomRight()
            }

            # Find nearest corner
            nearest = min(corners.items(), key=lambda kv: (kv[1] - pos).manhattanLength())
            self._resize_edge = nearest[0]
            self._resizing = True
            self._start_pos = event.pos()
            self._start_rect = QRectF(self.rect())

            # change cursor to match
            cursor_map = {
                "top_left": Qt.CursorShape.SizeFDiagCursor,
                "top_right": Qt.CursorShape.SizeBDiagCursor,
                "bottom_left": Qt.CursorShape.SizeBDiagCursor,
                "bottom_right": Qt.CursorShape.SizeFDiagCursor,
            }
            self.setCursor(cursor_map[self._resize_edge])

        elif event.button() == Qt.MouseButton.LeftButton and self._resize_edge:
            # Left button + near an edge/corner = resize
            self._resizing = True
            self._start_pos = event.pos()
            self._start_rect = QRectF(self.rect())
        else:
            # Otherwise, default movable/selectable behavior
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self._resizing and self._resize_edge:
            diff = event.pos() - self._start_pos
            rect = QRectF(self._start_rect)

            # Apply deltas based on which edge is grabbed
            if "left" in self._resize_edge:
                rect.setLeft(rect.left() + diff.x())
            if "right" in self._resize_edge:
                rect.setRight(rect.right() + diff.x())
            if "top" in self._resize_edge:
                rect.setTop(rect.top() + diff.y())
            if "bottom" in self._resize_edge:
                rect.setBottom(rect.bottom() + diff.y())

            # Normalize ensures that left<right and top<bottom
            rect = rect.normalized()

            self.setRect(rect)
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._resize_edge = None
        super().mouseReleaseEvent(event)



from PIL import Image
from PIL.ImageQt import ImageQt

import os, sys
from contextlib import contextmanager

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PyQt5.QtWidgets import QApplication


@contextmanager
def suppress_stderr():
    original_fd = os.dup(sys.stderr.fileno())
    devnull = open(os.devnull, 'w')
    os.dup2(devnull.fileno(), sys.stderr.fileno())
    try:
        yield
    finally:
        sys.stderr.flush()
        os.dup2(original_fd, sys.stderr.fileno())
        os.close(original_fd)
        devnull.close()


def selection_prompt(pil_img):
    with suppress_stderr():
        app = QApplication(sys.argv)
        qimg = ImageQt(pil_img)
        viewer = QtImageViewer(QPixmap.fromImage(qimg), enable_select=True)
        # Show viewer and run application.
        viewer.show()
        app.exec()
    return viewer.selection_rect

def field_selection_prompt(pil_img, fields):
    with suppress_stderr():
        app = QApplication(sys.argv)
        qimg = ImageQt(pil_img)
        viewer = QtImageViewer(QPixmap.fromImage(qimg), enable_select=False)
        for (nm, field) in fields:
            viewer.addRect(nm, field['x'], field['y'], field['width'], field['height'])
        # Show viewer and run application.
        viewer.show()
        app.exec()
    return viewer.selected_field
