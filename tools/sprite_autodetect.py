"""Automated sprite bounding-box detection via alpha-channel connected components.

Dev tool only (Pillow, per the project's stated tech stack) — not a runtime
dependency of the game itself.

The atlas PNGs (felix0-4.png, hammer0-3.png) have a fully transparent
background (alpha=0) around each isolated sprite. This script finds every
connected group of non-transparent pixels via flood fill, computes its
bounding box, and writes an annotated preview image with each box numbered
so the boxes can be identified by inspection and mapped to sprite names.

Usage:
    python3 tools/sprite_autodetect.py <atlas.png> <output_prefix>

Produces:
    <output_prefix>_boxes.json   — list of {"id": N, "bbox": [x, y, w, h]}
    <output_prefix>_preview.png  — atlas with numbered boxes drawn on it
"""
import sys
import json
from collections import deque
from PIL import Image, ImageDraw


def find_components(img, alpha_threshold=10, min_area=4):
    width, height = img.size
    pixels = img.load()
    visited = bytearray(width * height)
    components = []

    for start_y in range(height):
        for start_x in range(width):
            idx = start_y * width + start_x
            if visited[idx]:
                continue
            alpha = pixels[start_x, start_y][3]
            if alpha <= alpha_threshold:
                visited[idx] = 1
                continue

            # BFS flood fill (8-connectivity so diagonal-touching pixels merge)
            queue = deque([(start_x, start_y)])
            visited[idx] = 1
            min_x = max_x = start_x
            min_y = max_y = start_y
            area = 0

            while queue:
                x, y = queue.popleft()
                area += 1
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y

                for dx, dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        nidx = ny * width + nx
                        if not visited[nidx]:
                            visited[nidx] = 1
                            if pixels[nx, ny][3] > alpha_threshold:
                                queue.append((nx, ny))

            if area >= min_area:
                components.append({
                    "bbox": [min_x, min_y, max_x - min_x + 1, max_y - min_y + 1],
                    "area": area,
                })

    return components


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    atlas_path, out_prefix = sys.argv[1], sys.argv[2]
    img = Image.open(atlas_path).convert("RGBA")
    components = find_components(img)

    # Sort top-to-bottom, left-to-right for readable numbering
    components.sort(key=lambda c: (c["bbox"][1] // 20, c["bbox"][0]))
    for i, c in enumerate(components):
        c["id"] = i

    with open(f"{out_prefix}_boxes.json", "w") as f:
        json.dump(components, f, indent=2)

    preview = img.copy()
    draw = ImageDraw.Draw(preview)
    for c in components:
        x, y, w, h = c["bbox"]
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(255, 0, 255, 255), width=1)
        draw.text((x, max(0, y - 9)), str(c["id"]), fill=(255, 0, 255, 255))
    preview.save(f"{out_prefix}_preview.png")

    print(f"Found {len(components)} components")
    print(f"Wrote {out_prefix}_boxes.json and {out_prefix}_preview.png")


if __name__ == "__main__":
    main()
