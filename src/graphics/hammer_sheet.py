"""The hammer effect sprites (hammer0-3.png)."""

import os

import pygame

from paths import ASSET_DIR


class HammerSheet:
    def __init__(self):
        self._atlases = {}
        self._cache = {}

    def _get_atlas(self, variant):
        if variant not in self._atlases:
            path = os.path.join(ASSET_DIR, f"hammer{variant}.png")
            surface = pygame.image.load(path).convert_alpha()
            self._atlases[variant] = surface
        return self._atlases[variant]

    def get_sprite(self, name, frame=0, variant=0):
        cache_key = (name, frame, variant)
        if cache_key in self._cache:
            return self._cache[cache_key]

        from exe_data.sprite_data import HAMMER_SPRITES
        frames = HAMMER_SPRITES.get(name)
        if not frames:
            raise KeyError(f"Unknown hammer sprite: {name}")

        x, y, w, h = frames[frame]
        atlas = self._get_atlas(variant)
        surface = atlas.subsurface(pygame.Rect(x, y, w, h)).copy()
        self._cache[cache_key] = surface
        return surface
