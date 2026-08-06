from PySide6.QtGui import QPixmap, QPainter, QColor, QIcon, QPen, QPolygonF, QPainterPath
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


def make_profile_icon(hex_color, size=24):
    """Person silhouette (head + shoulders) used for profile identity icons."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size
    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 45)
    c_shade = _adjust(hex_color, -35)

    p.setPen(Qt.NoPen)
    p.setBrush(c_shade)
    p.drawEllipse(int(s * 0.30), int(s * 0.06), int(s * 0.40), int(s * 0.42))

    p.setBrush(c_main)
    p.drawEllipse(int(s * 0.28), int(s * 0.04), int(s * 0.44), int(s * 0.46))

    p.setBrush(c_lit)
    p.drawEllipse(int(s * 0.40), int(s * 0.16), int(s * 0.12), int(s * 0.12))

    p.setBrush(c_shade)
    path = QPainterPath()
    path.moveTo(s * 0.02, s * 1.0)
    path.cubicTo(s * 0.12, s * 0.60, s * 0.32, s * 0.56, s * 0.50, s * 0.56)
    path.cubicTo(s * 0.68, s * 0.56, s * 0.88, s * 0.60, s * 0.98, s * 1.0)
    path.closeSubpath()
    p.setBrush(c_main)
    p.drawPath(path)

    p.setPen(QPen(c_lit, max(1, s // 16)))
    p.drawLine(int(s * 0.16), int(s * 0.70), int(s * 0.38), int(s * 0.66))

    p.end()
    return QIcon(pm)


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
    "extras": "#fca311",
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
    key = ("profile", index % len(PROFILE_COLORS), size)
    if key not in _icon_cache:
        _icon_cache[key] = make_profile_icon(PROFILE_COLORS[key[1]], size)
    return _icon_cache[key]


def category_icon(cat_key, size=24):
    color = CATEGORY_COLORS.get(cat_key, "#888888")
    if cat_key == "general":
        return make_gear_icon(color, size)
    elif cat_key == "launch":
        return make_rocket_icon(color, size)
    elif cat_key in ("compat", "extras"):
        return make_gauge_icon(color, size)
    elif cat_key == "appearance":
        return make_palette_icon(color, size)
    elif cat_key == "integrations":
        return make_plug_icon(color, size)
    return block_icon(color, size)


# ── Tool icons (Tools tab) ──────────────────────────────────────────

def _pen(width):
    return QPen(Qt.NoPen)


def make_download_icon(hex_color, size=24):
    """Arrow pointing down into a tray (install)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c = QColor(hex_color)
    pw = max(1, s // 10)
    p.setPen(QPen(c, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(int(s * 0.5), int(s * 0.10), int(s * 0.5), int(s * 0.55))
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.30, s * 0.45), QPointF(s * 0.70, s * 0.45), QPointF(s * 0.5, s * 0.70),
    ]))
    p.setPen(QPen(c, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(int(s * 0.18), int(s * 0.80), int(s * 0.82), int(s * 0.80))
    p.end()
    return QIcon(pm)


def make_swap_icon(hex_color, size=24):
    """Two horizontal arrows pointing opposite ways (migrate)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c = QColor(hex_color)
    lit = _adjust(hex_color, 45)
    pw = max(1, s // 10)
    p.setPen(QPen(lit, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(int(s * 0.14), int(s * 0.40), int(s * 0.86), int(s * 0.40))
    p.setPen(Qt.NoPen)
    p.setBrush(lit)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.70, s * 0.25), QPointF(s * 0.86, s * 0.40), QPointF(s * 0.70, s * 0.55),
    ]))
    p.setPen(QPen(c, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(int(s * 0.86), int(s * 0.60), int(s * 0.14), int(s * 0.60))
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.30, s * 0.45), QPointF(s * 0.14, s * 0.60), QPointF(s * 0.30, s * 0.75),
    ]))
    p.end()
    return QIcon(pm)


def make_list_icon(hex_color, size=24):
    """Three bullet lines (version manager)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c = QColor(hex_color)
    lit = _adjust(hex_color, 45)
    pw = max(2, s // 9)
    for i, (col, x) in enumerate([(lit, 0.18), (c, 0.30), (lit, 0.42)]):
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawEllipse(int(s * 0.12), int(s * x - pw / 2), pw * 2, pw * 2)
        p.setPen(QPen(col, pw, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawLine(int(s * 0.30), int(s * x), int(s * 0.88), int(s * x))
    p.end()
    return QIcon(pm)


def make_cube_icon(hex_color, size=24):
    """Isometric 3D box (addons/resource packs)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 55)
    c_shade = _adjust(hex_color, -40)
    p.setPen(Qt.NoPen)
    p.setBrush(c_lit)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.50, s * 0.10), QPointF(s * 0.88, s * 0.30), QPointF(s * 0.50, s * 0.50), QPointF(s * 0.12, s * 0.30),
    ]))
    p.setBrush(c_main)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.12, s * 0.30), QPointF(s * 0.50, s * 0.50), QPointF(s * 0.50, s * 0.88), QPointF(s * 0.12, s * 0.68),
    ]))
    p.setBrush(c_shade)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.50, s * 0.50), QPointF(s * 0.88, s * 0.30), QPointF(s * 0.88, s * 0.68), QPointF(s * 0.50, s * 0.88),
    ]))
    p.end()
    return QIcon(pm)


def make_shirt_icon(hex_color, size=24):
    """T-shirt silhouette (skin packs)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 45)
    p.setPen(Qt.NoPen)
    p.setBrush(c_lit)
    p.drawEllipse(int(s * 0.40), int(s * 0.08), int(s * 0.20), int(s * 0.20))
    p.setBrush(c_main)
    body = QPolygonF([
        QPointF(s * 0.30, s * 0.14), QPointF(s * 0.42, s * 0.06),
        QPointF(s * 0.58, s * 0.06), QPointF(s * 0.70, s * 0.14),
        QPointF(s * 0.86, s * 0.30), QPointF(s * 0.74, s * 0.44),
        QPointF(s * 0.66, s * 0.40), QPointF(s * 0.66, s * 0.92),
        QPointF(s * 0.34, s * 0.92), QPointF(s * 0.34, s * 0.40),
        QPointF(s * 0.26, s * 0.44), QPointF(s * 0.14, s * 0.30),
    ])
    p.drawPolygon(body)
    p.end()
    return QIcon(pm)


def make_camera_icon(hex_color, size=24):
    """Camera body with lens (screenshots)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 50)
    p.setPen(Qt.NoPen)
    p.setBrush(c_lit)
    p.drawRoundedRect(int(s * 0.30), int(s * 0.12), int(s * 0.40), int(s * 0.16), 2, 2)
    p.setBrush(c_main)
    p.drawRoundedRect(int(s * 0.10), int(s * 0.24), int(s * 0.80), int(s * 0.56), int(s * 0.08), int(s * 0.08))
    p.setBrush(c_lit)
    p.drawEllipse(int(s * 0.34), int(s * 0.36), int(s * 0.32), int(s * 0.32))
    p.setBrush(c_main)
    p.drawEllipse(int(s * 0.41), int(s * 0.43), int(s * 0.18), int(s * 0.18))
    p.end()
    return QIcon(pm)


def make_sliders_icon(hex_color, size=24):
    """Three vertical sliders (game configuration)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c = QColor(hex_color)
    lit = _adjust(hex_color, 45)
    sh = _adjust(hex_color, -30)
    pw = max(1, s // 11)
    for i, (x, knob) in enumerate([(0.22, 0.30), (0.50, 0.66), (0.78, 0.44)]):
        col = lit if i == 1 else c
        p.setPen(QPen(col, pw, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawLine(int(s * x), int(s * 0.12), int(s * x), int(s * 0.88))
        p.setPen(Qt.NoPen)
        p.setBrush(sh)
        p.drawEllipse(int(s * x - pw), int(s * knob - pw), pw * 2, pw * 2)
        p.setBrush(col)
        p.drawEllipse(int(s * x - pw * 0.7), int(s * knob - pw * 0.7), int(pw * 1.4), int(pw * 1.4))
    p.end()
    return QIcon(pm)


def make_sparkle_icon(hex_color, size=24):
    """Four-point star sparkle (shaders)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c = QColor(hex_color)
    lit = _adjust(hex_color, 50)
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.50, s * 0.06), QPointF(s * 0.60, s * 0.40), QPointF(s * 0.94, s * 0.50),
        QPointF(s * 0.60, s * 0.60), QPointF(s * 0.50, s * 0.94), QPointF(s * 0.40, s * 0.60),
        QPointF(s * 0.06, s * 0.50), QPointF(s * 0.40, s * 0.40),
    ]))
    p.setBrush(lit)
    p.drawEllipse(int(s * 0.22), int(s * 0.16), int(s * 0.14), int(s * 0.14))
    p.drawEllipse(int(s * 0.66), int(s * 0.70), int(s * 0.12), int(s * 0.12))
    p.end()
    return QIcon(pm)


def make_folder_icon(hex_color, size=24):
    """Folder with tab (open data folder)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 50)
    p.setPen(Qt.NoPen)
    p.setBrush(c_lit)
    p.drawRoundedRect(int(s * 0.10), int(s * 0.30), int(s * 0.80), int(s * 0.52), 3, 3)
    p.setBrush(c_main)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.10, s * 0.30), QPointF(s * 0.34, s * 0.30),
        QPointF(s * 0.44, s * 0.40), QPointF(s * 0.90, s * 0.40),
        QPointF(s * 0.90, s * 0.82), QPointF(s * 0.10, s * 0.82),
    ]))
    p.end()
    return QIcon(pm)


def make_search_icon(hex_color, size=24):
    """Magnifying glass (verify hardware)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c = QColor(hex_color)
    pw = max(2, s // 8)
    p.setPen(QPen(c, pw, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(int(s * 0.20), int(s * 0.20), int(s * 0.40), int(s * 0.40))
    p.setPen(QPen(c, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(int(s * 0.55), int(s * 0.55), int(s * 0.86), int(s * 0.86))
    p.end()
    return QIcon(pm)


def make_shield_icon(hex_color, size=24):
    """Shield with a check (compatible range)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    c_main = QColor(hex_color)
    c_lit = _adjust(hex_color, 50)
    p.setPen(Qt.NoPen)
    p.setBrush(c_main)
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.50, s * 0.06), QPointF(s * 0.90, s * 0.18),
        QPointF(s * 0.84, s * 0.62), QPointF(s * 0.50, s * 0.94),
        QPointF(s * 0.16, s * 0.62), QPointF(s * 0.10, s * 0.18),
    ]))
    p.setPen(QPen(c_lit, max(2, s // 9), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(QPolygonF([
        QPointF(s * 0.36, s * 0.50), QPointF(s * 0.46, s * 0.60), QPointF(s * 0.66, s * 0.38),
    ]))
    p.end()
    return QIcon(pm)


TOOL_ICON_KINDS = {
    "download": make_download_icon,
    "swap": make_swap_icon,
    "list": make_list_icon,
    "cube": make_cube_icon,
    "shirt": make_shirt_icon,
    "camera": make_camera_icon,
    "sliders": make_sliders_icon,
    "sparkle": make_sparkle_icon,
    "folder": make_folder_icon,
    "search": make_search_icon,
    "shield": make_shield_icon,
    "plug": make_plug_icon,
}


def tool_icon(kind, hex_color="#888888", size=24):
    """Return a vector icon for a Tools tab tool by kind name."""
    maker = TOOL_ICON_KINDS.get(kind, make_block_icon)
    cache_key = ("tool", kind, hex_color, size)
    if cache_key not in _icon_cache:
        _icon_cache[cache_key] = maker(hex_color, size)
    return _icon_cache[cache_key]
