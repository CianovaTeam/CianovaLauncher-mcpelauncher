from PySide6.QtGui import QPixmap, QPainter, QColor, QIcon, QPen, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF
import math


def make_gear_icon(hex_color, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(hex_color)
    p.setPen(QPen(c, max(2, size // 8), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    cx, cy = size / 2, size / 2
    r = size * 0.28
    p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
    p.setBrush(c)
    p.drawEllipse(int(cx - r * 0.35), int(cy - r * 0.35), int(r * 0.7), int(r * 0.7))
    p.end()
    return QIcon(pm)


def make_rocket_icon(hex_color, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(hex_color)
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    poly = QPolygonF([
        QPointF(size * 0.75, size * 0.25),
        QPointF(size * 0.85, size * 0.15),
        QPointF(size * 0.75, size * 0.15),
        QPointF(size * 0.25, size * 0.65),
        QPointF(size * 0.15, size * 0.85),
        QPointF(size * 0.35, size * 0.75),
    ])
    p.drawPolygon(poly)
    p.end()
    return QIcon(pm)


def make_gauge_icon(hex_color, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(hex_color)
    p.setPen(QPen(c, max(2, size // 8), Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(size * 0.15, size * 0.15, size * 0.7, size * 0.7), 0, 180 * 16)
    p.drawLine(QPointF(size * 0.5, size * 0.5), QPointF(size * 0.7, size * 0.3))
    p.end()
    return QIcon(pm)


def make_palette_icon(hex_color, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(hex_color)
    p.setPen(QPen(c, max(2, size // 8)))
    p.setBrush(c)
    p.drawEllipse(QRectF(size * 0.15, size * 0.2, size * 0.7, size * 0.6))
    p.setBrush(Qt.white)
    p.drawEllipse(int(size * 0.35), int(size * 0.35), int(size * 0.15), int(size * 0.15))
    p.end()
    return QIcon(pm)


def make_plug_icon(hex_color, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(hex_color)
    p.setPen(QPen(c, max(2, size // 8), Qt.SolidLine, Qt.RoundCap))
    p.setBrush(c)
    p.drawRoundedRect(int(size * 0.3), int(size * 0.3), int(size * 0.4), int(size * 0.4), 4, 4)
    p.drawLine(int(size * 0.4), int(size * 0.3), int(size * 0.4), int(size * 0.15))
    p.drawLine(int(size * 0.6), int(size * 0.3), int(size * 0.6), int(size * 0.15))
    p.end()
    return QIcon(pm)


def make_block_icon(hex_color, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size
    inset = max(1, s // 12)
    r = max(2, s // 8)
    pw = max(1, s // 10)

    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 60)
    c_shade = _adjust(hex_color, -35)
    c_highlight = _adjust(hex_color, 90)

    inner = s - 2 * inset

    p.setPen(Qt.NoPen)
    p.setBrush(c_shade)
    p.drawRoundedRect(inset, inset, inner, inner, r, r)

    p.setBrush(c_main)
    p.drawRoundedRect(inset + pw, inset + pw, inner - 2 * pw, inner - 2 * pw, r - 1, r - 1)

    p.setPen(QPen(c_lit, pw))
    p.setBrush(Qt.NoBrush)
    top_edge = inset + pw // 2
    top_rect = (top_edge, top_edge, inner - 2 * pw, inner - 2 * pw)
    p.drawRoundedRect(*top_rect, r - 2, r - 2)

    dot = max(1, s // 10)
    p.setPen(Qt.NoPen)
    p.setBrush(c_highlight)
    p.drawEllipse(inset + pw * 2, inset + pw * 2, dot, dot)

    p.end()
    return QIcon(pm)


def _adjust(hex_color, amount):
    c = QColor(hex_color)
    h, s, l, a = c.getHsl()
    return QColor.fromHsl(h, s, min(max(l + amount, 0), 255), a)


PROFILE_COLORS = [
    "#2cc96b",
    "#fca311",
    "#ef4444",
    "#3b82f6",
    "#a855f7",
    "#ec4899",
    "#14b8a6",
    "#f97316",
    "#84cc16",
    "#06b6d4",
    "#8b5cf6",
    "#e11d48",
    "#0ea5e9",
    "#d946ef",
    "#22c55e",
]

CATEGORY_COLORS = {
    "general": "#8b8b8b",
    "launch": "#2cc96b",
    "compat": "#fca311",
    "appearance": "#a855f7",
    "integrations": "#3b82f6",
}

_icon_cache = {}


def block_icon(color_key, size=24):
    cache_key = (color_key, size)
    if cache_key not in _icon_cache:
        _icon_cache[cache_key] = make_block_icon(color_key, size)
    return _icon_cache[cache_key]


def profile_icon(index, size=24):
    return block_icon(PROFILE_COLORS[index % len(PROFILE_COLORS)], size)


def category_icon(cat_key, size=24):
    color = CATEGORY_COLORS.get(cat_key, "#888888")
    if cat_key == "general":
        return make_gear_icon(color, size)
    elif cat_key == "launch":
        return make_rocket_icon(color, size)
    elif cat_key == "compat":
        return make_gauge_icon(color, size)
    elif cat_key == "appearance":
        return make_palette_icon(color, size)
    elif cat_key == "integrations":
        return make_plug_icon(color, size)
    return block_icon(color, size)
