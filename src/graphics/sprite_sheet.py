import os

import pygame

from exe_data.exe_tables import BUILDING_PIECES, SPRITE_FRAMES
from paths import ASSET_DIR


class SpriteSheet:
    """Slices sprites out of the palette atlases (felix0..4.png), caching every slice."""

    def __init__(self):
        self._atlases = {}
        self._sprite_cache = {}
        self._frame_cache = {}
        self._piece_cache = {}
        self._region_cache = {}

    def _get_atlas(self, palette):
        if palette not in self._atlases:
            path = os.path.join(ASSET_DIR, f"felix{palette}.png")
            surface = pygame.image.load(path).convert_alpha()
            self._atlases[palette] = surface
        return self._atlases[palette]

    def get_sprite(self, name, frame=0, palette=0):
        cache_key = (name, frame, palette)
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]

        from exe_data.sprite_data import SPRITES
        frames = SPRITES.get(name)
        if not frames:
            raise KeyError(f"Unknown sprite: {name}")
        if frame >= len(frames):
            raise IndexError(f"Sprite '{name}' has {len(frames)} frames, requested {frame}")

        x, y, w, h = frames[frame]
        atlas = self._get_atlas(palette)
        surface = atlas.subsurface(pygame.Rect(x, y, w, h)).copy()
        self._sprite_cache[cache_key] = surface
        return surface

    def get_frame(self, frame_id, palette=0, is_flipped=False):
        """Return the exe-numbered sprite frame, optionally mirrored horizontally."""
        cache_key = (frame_id, palette, is_flipped)
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key]

        if not 0 <= frame_id < len(SPRITE_FRAMES):
            raise IndexError(f"Unknown sprite frame id: {frame_id}")
        surface = self._slice_atlas(SPRITE_FRAMES[frame_id], palette)
        if is_flipped:
            surface = pygame.transform.flip(surface, True, False)
        self._frame_cache[cache_key] = surface
        return surface

    def get_piece(self, piece_id, palette=0):
        """Return the exe-numbered building piece."""
        cache_key = (piece_id, palette)
        if cache_key in self._piece_cache:
            return self._piece_cache[cache_key]

        if not 0 <= piece_id < len(BUILDING_PIECES):
            raise IndexError(f"Unknown building piece id: {piece_id}")
        surface = self._slice_atlas(BUILDING_PIECES[piece_id], palette)
        self._piece_cache[cache_key] = surface
        return surface

    def get_region(self, region, palette=0):
        """Return an atlas rectangle (x, y, width, height); raises ValueError if it leaves the atlas."""
        cache_key = (tuple(region), palette)
        if cache_key in self._region_cache:
            return self._region_cache[cache_key]
        surface = self._slice_atlas(region, palette)
        self._region_cache[cache_key] = surface
        return surface

    def _slice_atlas(self, region, palette):
        x, y, w, h = region
        return self._get_atlas(palette).subsurface(pygame.Rect(x, y, w, h)).copy()

    def get_frame_count(self, name):
        from exe_data.sprite_data import SPRITES
        frames = SPRITES.get(name)
        return len(frames) if frames else 0
