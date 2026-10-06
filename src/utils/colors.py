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
    r = int(max(0, min(255, r + amount if isinstance(amount, (int, float)) and abs(amount) > 1 else r * amount)))
    g = int(max(0, min(255, g + amount if isinstance(amount, (int, float)) and abs(amount) > 1 else g * amount)))
    b = int(max(0, min(255, b + amount if isinstance(amount, (int, float)) and abs(amount) > 1 else b * amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def desaturate_color(hex_color, factor=0.45):
    """Reduce saturation of hex_color by factor (0.0 to 1.0) using perceived luminance."""
    if not hex_color or not hex_color.startswith("#"):
        return hex_color
    r, g, b = _hex_to_rgb(hex_color)
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    r = int(round(r * (1.0 - factor) + gray * factor))
    g = int(round(g * (1.0 - factor) + gray * factor))
    b = int(round(b * (1.0 - factor) + gray * factor))
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def blend_colors(base_hex, tint_hex, tint_factor, desaturate=0.45):
    """
    Blend base_hex with a desaturated tint_hex by tint_factor (0.0 to 1.0).
    Produces a soft, subtle chromatic undertone on dark or light backgrounds.
    """
    if not base_hex or not tint_hex:
        return base_hex
    if not base_hex.startswith("#") or not tint_hex.startswith("#"):
        return base_hex
    tint_muted = desaturate_color(tint_hex, desaturate) if desaturate > 0 else tint_hex
    r1, g1, b1 = _hex_to_rgb(base_hex)
    r2, g2, b2 = _hex_to_rgb(tint_muted)
    r = int(round(r1 * (1.0 - tint_factor) + r2 * tint_factor))
    g = int(round(g1 * (1.0 - tint_factor) + g2 * tint_factor))
    b = int(round(b1 * (1.0 - tint_factor) + b2 * tint_factor))
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02x}{g:02x}{b:02x}"
