# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

# Disclaimer: this script is inspired by
# https://github.com/marcel-goldschen-ohm/PyQtImageViewer

"""Interactive signature-placement prompt.

A lightweight PDF viewer (custom-painted ``QWidget``, not ``QGraphicsView``)
that shows the whole document and lets the user either

  * click one of the existing empty signature fields (blue outlines), or
  * drag / click a rectangle of their own anywhere on any page.

Whatever is currently picked is highlighted; only one area can be picked at a
time. Pages are rendered on demand from the PDF.
"""

import os
import sys
import math
from collections import namedtuple
from contextlib import contextmanager

try:
    from PyQt6.QtCore import Qt, QRectF, QPointF, QRect
    from PyQt6.QtGui import (
        QImage, QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QRegion,
    )
    from PyQt6.QtWidgets import QApplication, QWidget
except ImportError:
    try:
        from PyQt5.QtCore import Qt, QRectF, QPointF, QRect
        from PyQt5.QtGui import (
            QImage, QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QRegion,
        )
        from PyQt5.QtWidgets import QApplication, QWidget
    except ImportError:
        raise ImportError("Requires PyQt (version 5 or 6)")

import fitz  # PyMuPDF


# --- result -----------------------------------------------------------------

# ``page`` is the page index.  Exactly one of ``field`` (the field's id/index)
# or ``area`` ({'x','y','width','height'} in that page's points) is set.
Selection = namedtuple("Selection", ["page", "field", "area"])


# --- tuning knobs -----------------------------------------------------------

GUTTER_PT = 16.0          # gap between stacked pages, in points
TILE_MARGIN_FRAC = 0.25   # render this much extra around the viewport
WHEEL_STEP_PX = 90.0      # a mouse-wheel tick scrolls this far (logical px)
TOUCHPAD_SCALE = 2.25     # pixelDelta() is followed at 2.25x (feels right)
ZOOM_PER_TICK = 1.10      # Ctrl+wheel: one 120-unit tick multiplies zoom by this
ZOOM_TOUCHPAD_SCALE = 5.0  # Ctrl+touchpad px deltas are small -> amplify them
MAX_ZOOM = 10.0            # 72 dpi x 8; beyond this only magnifies render blur
MIN_ZOOM = 0.5
DEFAULT_AREA_W_PT = 92.0  # one-click default area width, fixed in PDF points
DRAG_THRESHOLD_PX = 4.0   # movement below this counts as a click
EDGE_GRAB_PX = 8.0        # resize-zone width, in *screen* px (zoom independent)
HANDLE_PX = 8.0           # side of the square resize handles, in screen px
BOTTOM_PAD_PX = 64.0      # extra scroll room past the last page so the hint
                          # bar overlay doesn't cover it at the very bottom

COLOR_FIELD = QColor(0, 120, 215)
COLOR_PICK = QColor(255, 140, 0)
COLOR_DIM = QColor(0, 0, 0, 110)
COLOR_PAGE = QColor(255, 255, 255)
COLOR_PAGE_BORDER = QColor(180, 180, 180)
COLOR_BG = QColor(64, 64, 64)

_EDGE_CURSORS = {
    "top_left": Qt.CursorShape.SizeFDiagCursor,
    "bottom_right": Qt.CursorShape.SizeFDiagCursor,
    "top_right": Qt.CursorShape.SizeBDiagCursor,
    "bottom_left": Qt.CursorShape.SizeBDiagCursor,
    "left": Qt.CursorShape.SizeHorCursor,
    "right": Qt.CursorShape.SizeHorCursor,
    "top": Qt.CursorShape.SizeVerCursor,
    "bottom": Qt.CursorShape.SizeVerCursor,
}


def _covers(clip, need, eps=0.5):
    """True if ``clip`` contains ``need`` (both QRectF, page points).

    A small tolerance avoids re-rendering every frame when a page fits fully
    in the viewport and ``need`` lands exactly on the tile's edge.
    """
    return (clip.left() <= need.left() + eps
            and clip.top() <= need.top() + eps
            and clip.right() + eps >= need.right()
            and clip.bottom() + eps >= need.bottom())


class _Tile:
    """A rendered clip of one page, kept 1:1 with the current zoom/dpr."""

    __slots__ = ("zoom", "dpr", "clip", "pixmap", "image")

    def __init__(self, zoom, dpr, clip, pixmap, image):
        self.zoom = zoom
        self.dpr = dpr
        self.clip = clip        # QRectF in page-local points
        self.pixmap = pixmap    # keep the fitz.Pixmap alive: QImage borrows it
        self.image = image


class PdfSelectView(QWidget):
    """Whole-document viewer with field-click / rectangle-drag selection."""

    def __init__(self, doc, fields, page=0, parent=None):
        super().__init__(parent)
        self._doc = doc
        self._start_page = max(0, min(page, doc.page_count - 1))

        # Fields grouped by page: {page_idx: [(field_id, QRectF page-local), ...]}
        self._fields_by_page = {}
        for field_id, page_idx, rect in fields:
            self._fields_by_page.setdefault(page_idx, []).append(
                (field_id, QRectF(rect["x"], rect["y"],
                                  rect["width"], rect["height"]))
            )

        # Page layout in "document points": a vertical stack, narrow pages
        # centred.  Each entry: {"w","h","x","y"} (x,y = top-left in doc space).
        self._pages = []
        y = 0.0
        widest = 1.0
        for i in range(doc.page_count):
            r = doc[i].rect
            widest = max(widest, r.width)
        for i in range(doc.page_count):
            r = doc[i].rect
            self._pages.append({"w": r.width, "h": r.height,
                                "x": (widest - r.width) / 2.0, "y": y})
            y += r.height + GUTTER_PT
        self.stack_width = widest
        self.total_height = max(0.0, y - GUTTER_PT)

        # View transform: screen = view + doc * zoom  (logical px).
        self.zoom = 1.0
        self.view_x = 0.0
        self.view_y = 0.0
        self._initialized = False

        # Current pick: None | ("field", page, field_id)
        #                    | ("area",  page, {x,y,width,height})
        self.pick = None
        # The committed Selection the caller reads after exec(); (window close keeps None).
        self.result = None

        # Interaction state.
        self._mode = None
        self._press = (0.0, 0.0)
        self._dragged = False
        self._drag_page = None
        self._drag_anchor = (0.0, 0.0)   # page-local anchor of a new area
        self._resize_edge = None
        self._resize_relative = False
        self._press_corner = (0.0, 0.0)
        self._press_local = (0.0, 0.0)
        self._start_rect = None
        self._pan_start = None
        self._field_hit = None
        self._hover_field = None   # (field_id, page) under the cursor, or None

        # Rendered tiles, one per visible page.
        self._tiles = {}

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)
        self.setWindowTitle("Select signature location")
        self.resize(1100, 850)

    # -- geometry helpers ---------------------------------------------------

    def _clamp_view(self, vx, vy):
        vw, vh = self.width(), self.height()
        sw = self.stack_width * self.zoom
        sh = self.total_height * self.zoom
        vx = (vw - sw) / 2.0 if sw <= vw else min(0.0, max(vw - sw, vx))
        # Allow scrolling BOTTOM_PAD_PX past the last page so the hint bar
        # overlay no longer covers it when scrolled all the way to the end.
        vy = (vh - sh) / 2.0 if sh <= vh else min(0.0, max(vh - sh - BOTTOM_PAD_PX, vy))
        return vx, vy

    def _doc_to_screen(self, dx, dy):
        return (self.view_x + dx * self.zoom, self.view_y + dy * self.zoom)

    def _screen_to_doc(self, sx, sy):
        return ((sx - self.view_x) / self.zoom, (sy - self.view_y) / self.zoom)

    def _page_screen_rect(self, i):
        p = self._pages[i]
        sx, sy = self._doc_to_screen(p["x"], p["y"])
        return QRectF(sx, sy, p["w"] * self.zoom, p["h"] * self.zoom)

    def _page_at_screen(self, sx, sy):
        dx, dy = self._screen_to_doc(sx, sy)
        for i, p in enumerate(self._pages):
            if (p["x"] <= dx <= p["x"] + p["w"]
                    and p["y"] <= dy <= p["y"] + p["h"]):
                return i
        return None

    def _screen_to_page_local(self, i, sx, sy):
        p = self._pages[i]
        dx, dy = self._screen_to_doc(sx, sy)
        return (dx - p["x"], dy - p["y"])

    def _page_local_rect_to_screen(self, i, rect):
        """rect: dict/QRectF in page-local points -> QRectF in screen px."""
        p = self._pages[i]
        if isinstance(rect, dict):
            x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
        else:
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        sx, sy = self._doc_to_screen(p["x"] + x, p["y"] + y)
        return QRectF(sx, sy, w * self.zoom, h * self.zoom)

    def _current_page(self):
        """The page the badge names: the one under the viewport centre."""
        cy = self.height() / 2.0
        best, best_d = 0, None
        for i in range(len(self._pages)):
            r = self._page_screen_rect(i)
            if r.top() <= cy <= r.bottom():
                return i
            d = min(abs(r.top() - cy), abs(r.bottom() - cy))
            if best_d is None or d < best_d:
                best, best_d = i, d
        return best

    # -- initial fit --------------------------------------------------------

    def _fit_page(self, i):
        """Zoom so page ``i`` fills the window, centred horizontally"""
        p = self._pages[i]
        vw, vh = self.width(), self.height()
        z = min(vw / p["w"], vh / p["h"]) * 0.98
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, z))
        self.view_x = vw / 2.0 - (p["x"] + p["w"] / 2.0) * self.zoom
        self.view_y = -p["y"] * self.zoom
        self.view_x, self.view_y = self._clamp_view(self.view_x, self.view_y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initialized and self.width() > 1 and self.height() > 1:
            self._initialized = True
            self._fit_page(self._start_page)
        else:
            self.view_x, self.view_y = self._clamp_view(self.view_x, self.view_y)
        self.update()

    # -- tile rendering -----------------------------------------------------

    def _render_tile(self, i, clip_local):
        dpr = self.devicePixelRatioF()
        scale = self.zoom * dpr
        page = self._doc[i]
        fclip = fitz.Rect(clip_local.x(), clip_local.y(),
                          clip_local.x() + clip_local.width(),
                          clip_local.y() + clip_local.height())
        pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale),
                             clip=fclip, alpha=False)
        # QImage borrows pm.samples -> the _Tile keeps pm alive.
        img = QImage(pm.samples, pm.width, pm.height, pm.stride,
                     QImage.Format.Format_RGB888)
        img.setDevicePixelRatio(dpr)
        return _Tile(self.zoom, dpr, QRectF(clip_local), pm, img)

    def _ensure_tile(self, i):
        """Make sure page ``i``'s visible region (+margin) is cached."""
        psr = self._page_screen_rect(i)
        view = QRectF(0, 0, self.width(), self.height())
        vis = psr.intersected(view)
        if vis.isEmpty():
            return None

        # Region we actually need (no margin), in page-local points.
        nx, ny = self._screen_to_page_local(i, vis.left(), vis.top())
        need = QRectF(nx, ny, vis.width() / self.zoom, vis.height() / self.zoom)

        dpr = self.devicePixelRatioF()
        tile = self._tiles.get(i)
        if (tile is not None and tile.zoom == self.zoom and tile.dpr == dpr
                and _covers(tile.clip, need)):
            return tile

        # Cache miss: render visible + margin, clamped to the page.
        mx = self.width() * TILE_MARGIN_FRAC
        my = self.height() * TILE_MARGIN_FRAC
        want = vis.adjusted(-mx, -my, mx, my).intersected(psr)
        cx, cy = self._screen_to_page_local(i, want.left(), want.top())
        clip = QRectF(cx, cy, want.width() / self.zoom, want.height() / self.zoom)
        p = self._pages[i]
        clip = clip.intersected(QRectF(0, 0, p["w"], p["h"]))
        if clip.isEmpty():
            return None
        tile = self._render_tile(i, clip)
        self._tiles[i] = tile
        return tile

    # -- painting -----------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), COLOR_BG)

        visible = []
        view = QRectF(0, 0, self.width(), self.height())
        for i in range(len(self._pages)):
            psr = self._page_screen_rect(i)
            if not psr.intersected(view).isEmpty():
                visible.append(i)

        for i in visible:
            psr = self._page_screen_rect(i)
            painter.fillRect(psr, COLOR_PAGE)
            tile = self._ensure_tile(i)
            if tile is not None:
                p = self._pages[i]
                tsx, tsy = self._doc_to_screen(p["x"] + tile.clip.x(),
                                               p["y"] + tile.clip.y())
                painter.drawImage(QPointF(tsx, tsy), tile.image)
            painter.setPen(QPen(COLOR_PAGE_BORDER, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(psr)

        # Drop tiles for pages that scrolled off screen (flat memory).
        for i in list(self._tiles):
            if i not in visible:
                del self._tiles[i]

        self._draw_fields(painter, visible)
        self._draw_pick(painter, visible)
        self._draw_overlays(painter)
        painter.end()

    def _draw_fields(self, painter, visible):
        picked = (self.pick[1], self.pick[2]) if (self.pick
                  and self.pick[0] == "field") else None
        for i in visible:
            for field_id, rect in self._fields_by_page.get(i, []):
                if picked == (i, field_id):
                    continue  # drawn orange by _draw_pick
                hovered = self._hover_field == (field_id, i)
                screen = self._page_local_rect_to_screen(i, rect)
                if hovered:
                    painter.setBrush(QBrush(QColor(0, 120, 215, 80)))
                else:
                    painter.setBrush(QBrush(QColor(0, 120, 215, 30)))
                painter.setPen(QPen(COLOR_FIELD, 2))
                painter.drawRect(screen)
                self._draw_field_label(
                    painter, screen, field_id, COLOR_FIELD)

    def _draw_field_label(self, painter, screen, field_id, color):
        """Write the field's index centred in its box, scaled to fit."""
        size = max(6.0, min(screen.height() * 0.6, screen.width() * 0.6, 40.0))
        f = QFont("Sans")
        f.setPointSizeF(size)
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(QPen(color))
        painter.drawText(screen, Qt.AlignmentFlag.AlignCenter, str(field_id))

    def _draw_pick(self, painter, visible):
        if self.pick is None:
            return
        kind, page, payload = self.pick
        if kind == "field":
            rect = None
            for field_id, r in self._fields_by_page.get(page, []):
                if field_id == payload:
                    rect = r
                    break
            if rect is None:
                return
            screen = self._page_local_rect_to_screen(page, rect)
        else:
            screen = self._page_local_rect_to_screen(page, payload)

        # Dim the whole viewport around whatever is picked.
        self._dim_screen(painter, screen)

        painter.setBrush(QBrush(QColor(255, 140, 0, 40)))
        painter.setPen(QPen(COLOR_PICK, 2))
        painter.drawRect(screen)

        if kind == "field":
            self._draw_field_label(painter, screen, payload, COLOR_PICK)

        if kind == "area":
            painter.setBrush(QBrush(COLOR_PICK))
            painter.setPen(Qt.PenStyle.NoPen)
            for hx, hy in self._handle_centers(screen):
                painter.drawRect(QRectF(hx - HANDLE_PX / 2, hy - HANDLE_PX / 2,
                                        HANDLE_PX, HANDLE_PX))

    def _dim_screen(self, painter, screen):
        # Darken the entire viewport except the picked rectangle.  Snapping to
        # whole pixels keeps the cut-out's edges from showing antialiased seams.
        s = QRect(round(screen.left()), round(screen.top()),
                  round(screen.width()), round(screen.height()))
        painter.save()
        painter.setClipRegion(QRegion(self.rect()).subtracted(QRegion(s)))
        painter.fillRect(self.rect(), COLOR_DIM)
        painter.restore()

    def _handle_centers(self, screen):
        l, t, r, b = (screen.left(), screen.top(),
                      screen.right(), screen.bottom())
        cx, cy = (l + r) / 2, (t + b) / 2
        return [(l, t), (cx, t), (r, t), (l, cy), (r, cy),
                (l, b), (cx, b), (r, b)]

    def _draw_overlays(self, painter):
        # Page badge.
        idx = self._current_page()
        badge = f"Page {idx + 1} / {len(self._pages)}"
        painter.setFont(QFont("Sans", 10))
        fm = QFontMetrics(painter.font())
        bw = fm.horizontalAdvance(badge) + 16
        bh = fm.height() + 8
        br = QRect(self.width() - bw - 12, 12, bw, bh)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.drawRoundedRect(br, 4, 4)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(br, Qt.AlignmentFlag.AlignCenter, badge)

        # Hint bar.
        hint = ("[drag] create/move area   [click] pick/new   "
                "[r-drag] pan/resize   [ctrl + wheel/+/-/0]: zoom   [PgUp/PgDn or j/k] jump page   "
                "[enter] confirm   [esc/q] cancel")
        hh = fm.height() + 10
        hr = QRect(0, self.height() - hh, self.width(), hh)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(hr)
        painter.setPen(QPen(QColor(230, 230, 230)))
        painter.drawText(hr, Qt.AlignmentFlag.AlignCenter, hint)

    # -- hit testing --------------------------------------------------------

    def _field_at_screen(self, sx, sy):
        for i in range(len(self._pages)):
            if self._page_screen_rect(i).intersected(
                    QRectF(0, 0, self.width(), self.height())).isEmpty():
                continue
            for field_id, rect in self._fields_by_page.get(i, []):
                if self._page_local_rect_to_screen(i, rect).contains(
                        QPointF(sx, sy)):
                    return (field_id, i)
        return None

    def _area_screen_rect(self):
        if self.pick is None or self.pick[0] != "area":
            return None
        return self._page_local_rect_to_screen(self.pick[1], self.pick[2])

    def _edge_at_screen(self, sx, sy):
        """Edge/corner name of the picked area near (sx,sy), or None."""
        sr = self._area_screen_rect()
        if sr is None:
            return None
        m = EDGE_GRAB_PX
        # Only within a small band around the rectangle.
        near = sr.adjusted(-m, -m, m, m)
        if not near.contains(QPointF(sx, sy)):
            return None
        vert = ("top" if abs(sy - sr.top()) <= m else
                "bottom" if abs(sy - sr.bottom()) <= m else "")
        horz = ("left" if abs(sx - sr.left()) <= m else
                "right" if abs(sx - sr.right()) <= m else "")
        return "_".join(filter(None, (vert, horz))) or None

    def _inside_area(self, sx, sy):
        sr = self._area_screen_rect()
        return sr is not None and sr.contains(QPointF(sx, sy))

    # -- mouse --------------------------------------------------------------

    def mousePressEvent(self, event):
        sx, sy = event.position().x(), event.position().y()
        if event.button() == Qt.MouseButton.RightButton:
            # Right-drag on the picked area resizes it by the nearest
            # corner; anywhere else it pans the view.
            sr = self._area_screen_rect()
            if sr is not None and sr.contains(
                    QPointF(sx, sy)):
                self._begin_right_resize(sx, sy, sr)
            else:
                self._begin_pan(sx, sy)
        elif event.button() == Qt.MouseButton.LeftButton:
            self._left_press(sx, sy)
        event.accept()

    def mouseMoveEvent(self, event):
        sx, sy = event.position().x(), event.position().y()
        if self._mode == "pan":
            self._pan_to(sx, sy)
        elif self._mode is not None:
            self._left_move(sx, sy)
        else:
            self._update_cursor(sx, sy)
        event.accept()

    def mouseReleaseEvent(self, event):
        sx, sy = event.position().x(), event.position().y()
        if event.button() == Qt.MouseButton.RightButton:
            if self._mode in ("pan", "resize"):  # end pan / right-drag resize
                self._mode = None
                self._update_cursor(sx, sy)
        elif event.button() == Qt.MouseButton.LeftButton:
            self._left_release(sx, sy)
        event.accept()

    def _begin_pan(self, sx, sy):
        self._mode = "pan"
        self._pan_start = (sx, sy, self.view_x, self.view_y)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _pan_to(self, sx, sy):
        psx, psy, vx, vy = self._pan_start
        self.view_x, self.view_y = self._clamp_view(vx + (sx - psx),
                                                    vy + (sy - psy))
        self.update()

    def _begin_right_resize(self, sx, sy, sr):
        """Right-drag resize: grab the nearest corner of the picked area."""
        page = self.pick[1]
        rect = self.pick[2]
        corners = {
            "top_left": (rect["x"], rect["y"]),
            "top_right": (rect["x"] + rect["width"], rect["y"]),
            "bottom_left": (rect["x"], rect["y"] + rect["height"]),
            "bottom_right": (rect["x"] + rect["width"], rect["y"] + rect["height"]),
        }
        px, py = self._screen_to_page_local(page, sx, sy)
        edge = min(corners, key=lambda n: (corners[n][0] - px) ** 2
                   + (corners[n][1] - py) ** 2)
        self._mode = "resize"
        self._resize_edge = edge
        self._resize_relative = True          # move the corner by the drag delta
        self._press_corner = corners[edge]
        self._press_local = (px, py)
        self._start_rect = dict(rect)
        self._drag_page = page
        self._press = (sx, sy)
        self.setCursor(_EDGE_CURSORS[edge])

    def _left_press(self, sx, sy):
        self._press = (sx, sy)
        self._dragged = False

        if self.pick is not None and self.pick[0] == "area":
            edge = self._edge_at_screen(sx, sy)
            if edge:
                self._mode = "resize"
                self._resize_edge = edge
                self._resize_relative = False  # left grab: corner follows pointer
                self._start_rect = dict(self.pick[2])
                self._drag_page = self.pick[1]
                return
            if self._inside_area(sx, sy):
                self._mode = "move"
                self._start_rect = dict(self.pick[2])
                self._drag_page = self.pick[1]
                self._drag_anchor = self._screen_to_page_local(
                    self.pick[1], sx, sy)
                return

        hit = self._field_at_screen(sx, sy)
        if hit is not None:
            self._mode = "field"
            self._field_hit = hit
            return

        # Empty page (or gutter): candidate for area drag / click.
        self._mode = "areacreate"
        self._drag_page = self._page_at_screen(sx, sy)
        if self._drag_page is not None:
            self._drag_anchor = self._screen_to_page_local(
                self._drag_page, sx, sy)

    def _left_move(self, sx, sy):
        if (abs(sx - self._press[0]) > DRAG_THRESHOLD_PX
                or abs(sy - self._press[1]) > DRAG_THRESHOLD_PX):
            self._dragged = True

        if self._mode == "resize":
            self._do_resize(sx, sy)
        elif self._mode == "move":
            self._do_move(sx, sy)
        elif self._mode == "field":
            if self._dragged:
                # A drag that began on a field turns into a new area.
                _, page = self._field_hit
                self._mode = "areacreate"
                self._drag_page = page
                self._drag_anchor = self._screen_to_page_local(
                    page, self._press[0], self._press[1])
                self._do_areacreate(sx, sy)
        elif self._mode == "areacreate":
            if self._dragged:
                self._do_areacreate(sx, sy)

    def _left_release(self, sx, sy):
        mode = self._mode
        self._mode = None
        if mode in ("resize", "move"):
            self._update_cursor(sx, sy)
            return
        if mode == "field":
            if not self._dragged:
                field_id, page = self._field_hit
                self.pick = ("field", page, field_id)
            self.update()
        elif mode == "areacreate":
            if self._dragged and self._drag_page is not None:
                pass  # area already built live in _do_areacreate
            elif self.pick is not None:
                self.pick = None                      # click clears the pick
            elif self._drag_page is not None:
                self._create_default_area(sx, sy)     # click makes default area
            self.update()
        self._update_cursor(sx, sy)

    def _do_move(self, sx, sy):
        page = self._drag_page
        px, py = self._screen_to_page_local(page, sx, sy)
        r = self._start_rect
        nx = r["x"] + (px - self._drag_anchor[0])
        ny = r["y"] + (py - self._drag_anchor[1])
        pw, ph = self._pages[page]["w"], self._pages[page]["h"]
        nx = max(0.0, min(pw - r["width"], nx))
        ny = max(0.0, min(ph - r["height"], ny))
        self.pick = ("area", page,
                     {"x": nx, "y": ny, "width": r["width"], "height": r["height"]})
        self.update()

    def _do_resize(self, sx, sy):
        page = self._drag_page
        px, py = self._screen_to_page_local(page, sx, sy)
        if self._resize_relative:
            # Right-drag: move the grabbed corner by the drag delta (so a corner
            # grabbed from a distance does not jump to the pointer).
            px = self._press_corner[0] + (px - self._press_local[0])
            py = self._press_corner[1] + (py - self._press_local[1])
        pw, ph = self._pages[page]["w"], self._pages[page]["h"]
        px = max(0.0, min(pw, px))
        py = max(0.0, min(ph, py))
        r = dict(self._start_rect)
        left, top = r["x"], r["y"]
        right, bottom = r["x"] + r["width"], r["y"] + r["height"]
        if "left" in self._resize_edge:
            left = px
        if "right" in self._resize_edge:
            right = px
        if "top" in self._resize_edge:
            top = py
        if "bottom" in self._resize_edge:
            bottom = py
        x0, x1 = min(left, right), max(left, right)
        y0, y1 = min(top, bottom), max(top, bottom)
        min_pt = 4.0
        self.pick = ("area", page, {
            "x": x0, "y": y0,
            "width": max(min_pt, x1 - x0), "height": max(min_pt, y1 - y0),
        })
        self.update()

    def _do_areacreate(self, sx, sy):
        page = self._drag_page
        px, py = self._screen_to_page_local(page, sx, sy)
        pw, ph = self._pages[page]["w"], self._pages[page]["h"]
        ax, ay = self._drag_anchor
        x0, x1 = sorted((ax, px))
        y0, y1 = sorted((ay, py))
        # Clamp to the page the drag started on: an area never spans two pages.
        x0 = max(0.0, min(pw, x0)); x1 = max(0.0, min(pw, x1))
        y0 = max(0.0, min(ph, y0)); y1 = max(0.0, min(ph, y1))
        self.pick = ("area", page,
                     {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
        self.update()

    def _create_default_area(self, sx, sy):
        page = self._drag_page
        pw, ph = self._pages[page]["w"], self._pages[page]["h"]
        # Fixed size in PDF points -> same across documents, independent of page
        # width and zoom.  Clamp to the page in case it is very small.
        w = min(DEFAULT_AREA_W_PT, pw)
        h = w / 4.0                      # 4:1
        cx, cy = self._screen_to_page_local(page, sx, sy)
        x = max(0.0, min(pw - w, cx - w / 2.0))
        y = max(0.0, min(ph - h, cy - h / 2.0))
        self.pick = ("area", page, {"x": x, "y": y, "width": w, "height": h})

    def _update_cursor(self, sx, sy):
        if self.pick is not None and self.pick[0] == "area":
            edge = self._edge_at_screen(sx, sy)
            if edge:
                # Over the picked area's edges/interior the fields below are not
                # clickable, so suppress their hover highlight.
                self._set_hover(None)
                self.setCursor(_EDGE_CURSORS[edge])
                return
            if self._inside_area(sx, sy):
                self._set_hover(None)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
        hit = self._field_at_screen(sx, sy)
        self._set_hover(hit)
        if hit is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._page_at_screen(sx, sy) is not None:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _set_hover(self, hit):
        """hit is (field_id, page) or None; repaint only when it changes."""
        if hit != self._hover_field:
            self._hover_field = hit
            self.update()

    def leaveEvent(self, event):
        self._set_hover(None)
        super().leaveEvent(event)

    # -- wheel: scrolling & zoom -------------------------------------------

    def wheelEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        pos = event.position()
        angle_x, angle_y = event.angleDelta().x(), event.angleDelta().y()
        pixel_x, pixel_y = event.pixelDelta().x(), event.pixelDelta().y()
        event.accept()

        if ctrl:
            # A wheel tick is 120 units; a touchpad sends small px deltas, so
            # amplify those to a comparable zoom rate.
            delta = pixel_y * ZOOM_TOUCHPAD_SCALE if pixel_y else angle_y
            self._zoom_at(pos.x(), pos.y(),
                          math.exp(delta * math.log(ZOOM_PER_TICK) / 120.0))
        elif pixel_x or pixel_y:
            # Touchpad: follow the fingers at the distance they travelled.
            self._scroll_by(pixel_x * TOUCHPAD_SCALE, pixel_y * TOUCHPAD_SCALE)
        else:
            # Mouse wheel: a fixed step per 120-unit tick.
            self._scroll_by(angle_x / 120.0 * WHEEL_STEP_PX,
                            angle_y / 120.0 * WHEEL_STEP_PX)

    def _scroll_by(self, dx, dy):
        self.view_x, self.view_y = self._clamp_view(self.view_x + dx,
                                                    self.view_y + dy)
        self.update()

    def _zoom_at(self, sx, sy, factor):
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom:
            return
        dx, dy = self._screen_to_doc(sx, sy)
        self.zoom = new_zoom
        # Keep the doc point under the cursor fixed.
        self.view_x = sx - dx * self.zoom
        self.view_y = sy - dy * self.zoom
        self.view_x, self.view_y = self._clamp_view(self.view_x, self.view_y)
        self._tiles.clear()  # zoom changed -> tiles are the wrong resolution
        self.update()

    # -- keyboard -----------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._confirm()
        elif key in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()  # result stays None -> cancelled
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._zoom_at(self.width() / 2, self.height() / 2, ZOOM_PER_TICK)
        elif key == Qt.Key.Key_Minus:
            self._zoom_at(self.width() / 2, self.height() / 2, 1 / ZOOM_PER_TICK)
        elif key == Qt.Key.Key_0:
            self._fit_page(self._current_page())
            self._tiles.clear()
            self.update()
        elif key in (Qt.Key.Key_PageDown, Qt.Key.Key_J):
            self._jump_page(1)
        elif key in (Qt.Key.Key_PageUp, Qt.Key.Key_K):
            self._jump_page(-1)
        else:
            super().keyPressEvent(event)

    def _jump_page(self, delta):
        i = max(0, min(len(self._pages) - 1, self._current_page() + delta))
        self.view_y = -self._pages[i]["y"] * self.zoom
        self.view_x, self.view_y = self._clamp_view(self.view_x, self.view_y)
        self.update()

    def _confirm(self):
        if self.pick is None:
            return  # Enter with nothing picked does nothing; window stays open
        kind, page, payload = self.pick
        if kind == "field":
            self.result = Selection(page=page, field=payload, area=None)
        else:
            self.result = Selection(page=page, field=None, area=dict(payload))
        self.close()


@contextmanager
def suppress_stderr():
    original_fd = os.dup(sys.stderr.fileno())
    devnull = open(os.devnull, "w")
    os.dup2(devnull.fileno(), sys.stderr.fileno())
    try:
        yield
    finally:
        sys.stderr.flush()
        os.dup2(original_fd, sys.stderr.fileno())
        os.close(original_fd)
        devnull.close()


def selection_prompt(doc, fields, page=0):
    """Show the whole ``doc`` and let the user pick a field or drag an area.

    ``fields`` is an iterable of ``(field_id, page_idx, rect)`` where ``rect``
    is ``{'x','y','width','height'}`` in that page's points.  Returns a
    :data:`Selection`, or ``None`` if the user cancelled.
    """
    with suppress_stderr():
        app = QApplication.instance() or QApplication(sys.argv)
        view = PdfSelectView(doc, list(fields), page=page)
        view.show()
        app.exec()
    return view.result
