import os
from PIL import Image
import customtkinter as ctk
from src.utils.resource_path import resource_path

class ImageManager:
    _cache = {}

    @classmethod
    def get_image(cls, filename, size=(32, 32)):
        """
        Loads and caches a CTkImage.
        """
        cache_key = (filename, size)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        path = resource_path(filename)

        # Fallback for Flatpak
        if not os.path.exists(path):
            flatpak_path = os.path.join("/app/bin", filename)
            if os.path.exists(flatpak_path):
                path = flatpak_path

        if os.path.exists(path):
            try:
                pil_img = Image.open(path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                cls._cache[cache_key] = ctk_img
                return ctk_img
            except Exception as e:
                print(f"Error loading image {filename}: {e}")

        return None
