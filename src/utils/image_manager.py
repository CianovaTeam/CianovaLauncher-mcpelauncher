import os
from PIL import Image
from PySide6.QtGui import QPixmap, QImage, QIcon
from src.utils.resource_path import resource_path
from src.utils.logger import logger

class ImageManager:
    _cache = {}
    _max_cache_size = 50

    @classmethod
    def clear_cache(cls):
        """Clear cached pixmaps.

        Kept as a named companion to ``invalidate`` for callers that release
        optional UI assets after a cleanup operation.
        """
        cls._cache.clear()

    @classmethod
    def get_image(cls, filename, size=(32, 32)):
        """
        Loads and caches a QPixmap scaled to the specified size.
        """
        if isinstance(size, int):
            size = (size, size)
        cache_key = (filename, size)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # If filename is already an absolute path, use it directly
        if os.path.isabs(filename):
            path = filename
        else:
            path = resource_path(filename)

            # Fallback for Flatpak
            if not os.path.exists(path):
                flatpak_path = os.path.join("/app/bin", filename)
                if os.path.exists(flatpak_path):
                    path = flatpak_path

        if not os.path.isabs(path) and not os.path.exists(path):
            alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", filename)
            if os.path.exists(alt_path):
                path = alt_path

        if os.path.exists(path):
            try:
                if path.lower().endswith(".svg"):
                    icon = QIcon(path)
                    if not icon.isNull() and size:
                        from PySide6.QtCore import QSize
                        pixmap = icon.pixmap(QSize(size[0], size[1]))
                    else:
                        pixmap = QPixmap(path)
                else:
                    pixmap = QPixmap(path)

                if not pixmap.isNull():
                    if size and (pixmap.width() != size[0] or pixmap.height() != size[1]):
                        from PySide6.QtCore import Qt
                        pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)

                    if len(cls._cache) >= cls._max_cache_size:
                        cls._cache.pop(next(iter(cls._cache)))

                    cls._cache[cache_key] = pixmap
                    return pixmap
            except Exception as e:
                logger.warning("Error loading image %s: %s", filename, e)

        return None

    @classmethod
    def invalidate(cls, filename=None):
        """Invalidate specific file from cache or clear all cache if filename is None."""
        if not filename:
            cls._cache.clear()
            return
        keys_to_del = [k for k in cls._cache if k[0] == filename or (isinstance(k[0], str) and os.path.basename(k[0]) == os.path.basename(filename))]
        for k in keys_to_del:
            cls._cache.pop(k, None)

    @classmethod
    def get_icon(cls, filename):
        """
        Returns a QIcon from the filename.
        """
        if os.path.isabs(filename):
            path = filename
        else:
            path = resource_path(filename)
            if not os.path.exists(path):
                alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", filename)
                if os.path.exists(alt_path):
                    path = alt_path

        if os.path.exists(path):
            return QIcon(path)
        return QIcon()

    @classmethod
    def get_tinted_icon(cls, filename, color_hex, size=(24, 24)):
        """Loads an icon/SVG and tints it dynamically with the given color."""
        pix = cls.get_image(filename, size=size)
        if not pix or pix.isNull():
            return cls.get_icon(filename)
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainter, QColor
        tinted = QPixmap(pix.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pix)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color_hex))
        painter.end()
        return QIcon(tinted)
