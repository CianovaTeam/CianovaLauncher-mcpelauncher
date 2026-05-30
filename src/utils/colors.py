def hex_to_rgba(hex_color, opacity):
    if not hex_color or not hex_color.startswith("#"):
        return hex_color
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([x * 2 for x in h])
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {int(opacity * 255)})"


def adjust_color(hex_color, amount):
    if not hex_color or not hex_color.startswith("#"):
        return hex_color
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([x * 2 for x in h])
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = max(0, min(255, r + amount))
    g = max(0, min(255, g + amount))
    b = max(0, min(255, b + amount))
    return f"#{r:02x}{g:02x}{b:02x}"
