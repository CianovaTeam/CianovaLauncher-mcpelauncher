def _hex_to_rgb(hex_color):
    """Parse a ``#rgb``/``#rrggbb`` string into an ``(r, g, b)`` tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([x * 2 for x in h])
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_to_rgba(hex_color, opacity):
    if not hex_color or not hex_color.startswith("#"):
        return hex_color
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {int(opacity * 255)})"


def adjust_color(hex_color, amount):
    if not hex_color or not hex_color.startswith("#"):
        return hex_color
    r, g, b = _hex_to_rgb(hex_color)
    r = max(0, min(255, r + amount))
    g = max(0, min(255, g + amount))
    b = max(0, min(255, b + amount))
    return f"#{r:02x}{g:02x}{b:02x}"
