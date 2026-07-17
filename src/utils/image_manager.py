import os
from PIL import Image
from PySide6.QtGui import QPixmap, QImage, QIcon
from src.utils.resource_path import resource_path
from src.utils.logger import logger

class ImageManager:
    _cache = {}
    _max_cache_size = 50

    @classmethod
    def get_image(cls, filename, size=(32, 32)):
        """
        Loads and caches a QPixmap scaled to the specified size.
        """
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

        if os.path.exists(path):
            try:
                # We can load directly with QPixmap for common formats
                # but let's use PIL if we want to stay "functional as currently"
                # or just use QPixmap if it's simpler.
                # CustomTkinter's CTkImage allowed different images for light/dark.
                # Here we just use one for now as the original code did.

                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    if size:
                        from PySide6.QtCore import Qt
                        pixmap = pixmap.scaled(size[0], size[1], Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

                    # Simple cache eviction
                    if len(cls._cache) >= cls._max_cache_size:
                        # Remove a random item (or could be improved to LRU)
                        cls._cache.pop(next(iter(cls._cache)))

                    cls._cache[cache_key] = pixmap
                    return pixmap
            except Exception as e:
                logger.warning("Error loading image %s: %s", filename, e)

        return None

    @classmethod
    def get_icon(cls, filename):
        """
        Returns a QIcon from the filename.
        """
        path = resource_path(filename)
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()
