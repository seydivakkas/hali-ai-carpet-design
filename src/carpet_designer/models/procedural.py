"""Deterministic procedural carpet renderer used by the local demo mode."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageOps

if TYPE_CHECKING:
    from carpet_designer.domain.schemas import PromptRecipe


DEFAULT_PALETTE = ["#7A1F2B", "#162A5A", "#E8DCC3", "#B58A3A", "#2E1B16"]


class ProceduralCarpetGenerator:
    """Render presentation-quality, deterministic carpet concepts without model weights.

    This renderer is intentionally labelled as a demo engine. It keeps the full product
    workflow usable on CPU-only machines while the optional SDXL/LoRA artifacts are absent.
    """

    def generate(self, recipe: PromptRecipe, palette: list[str] | None = None) -> Image.Image:
        """Generate a carpet image from a structured prompt recipe."""
        colors = (palette or DEFAULT_PALETTE)[:]
        while len(colors) < 5:
            colors.append(DEFAULT_PALETTE[len(colors)])

        width = max(256, recipe.width)
        height = max(256, recipe.height)
        rng = random.Random(f"{recipe.seed}:{recipe.style_family or 'source_style'}")
        foreground = colors[:4]
        rng.shuffle(foreground)
        colors = foreground + colors[4:]
        image = Image.new("RGB", (width, height), colors[4])
        draw = ImageDraw.Draw(image)

        margin = max(18, min(width, height) // 28)
        self._draw_border(draw, width, height, margin, colors, recipe.border)
        field_box = (margin * 3, margin * 3, width - margin * 3, height - margin * 3)
        draw.rectangle(field_box, fill=colors[2])

        composition = recipe.composition or "central_medallion"
        motifs = recipe.motifs or ["diamond", "star", "ram_horn"]
        if composition == "central_medallion":
            self._draw_medallion(draw, field_box, colors, motifs, rng)
        elif composition in {"all_over_repeat", "corner_and_field", "panel"}:
            self._draw_repeat(draw, field_box, colors, motifs, rng)
        elif composition == "stripe":
            self._draw_stripes(draw, field_box, colors, motifs)
        elif composition == "concentric":
            self._draw_concentric(draw, field_box, colors, motifs)
        else:
            self._draw_directional(draw, field_box, colors, motifs)

        self._draw_corner_accents(draw, field_box, colors, motifs[0])
        self._add_woven_texture(image, max(2, min(width, height) // 320))
        return self.apply_symmetry(image, recipe.symmetry)

    @staticmethod
    def apply_symmetry(image: Image.Image, symmetry: str) -> Image.Image:
        """Apply the requested deterministic symmetry contract to demo output."""
        width, height = image.size
        half_width = width // 2
        half_height = height // 2
        if symmetry == "bilateral":
            left = image.crop((0, 0, half_width, height))
            result = image.copy()
            result.paste(left, (0, 0))
            result.paste(ImageOps.mirror(left), (width - half_width, 0))
            return result
        if symmetry == "quadrilateral":
            top_left = image.crop((0, 0, half_width, half_height))
            top = Image.new("RGB", (width, half_height))
            top.paste(top_left, (0, 0))
            top.paste(ImageOps.mirror(top_left), (width - half_width, 0))
            result = Image.new("RGB", (width, height))
            result.paste(top, (0, 0))
            result.paste(ImageOps.flip(top), (0, height - half_height))
            return result
        if symmetry == "rotational_2":
            top = image.crop((0, 0, width, half_height))
            result = image.copy()
            result.paste(top, (0, 0))
            result.paste(top.rotate(180), (0, height - half_height))
            return result
        if symmetry == "rotational_4":
            top_left = image.crop((0, 0, half_width, half_height))
            result = Image.new("RGB", (width, height))
            result.paste(top_left, (0, 0))
            result.paste(
                ImageOps.fit(top_left.rotate(-90, expand=True), (half_width, half_height)),
                (width - half_width, 0),
            )
            result.paste(
                ImageOps.fit(top_left.rotate(90, expand=True), (half_width, half_height)),
                (0, height - half_height),
            )
            result.paste(top_left.rotate(180), (width - half_width, height - half_height))
            return result
        return image

    def _draw_border(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        margin: int,
        colors: list[str],
        border: str,
    ) -> None:
        if border == "no_border":
            draw.rectangle((margin, margin, width - margin, height - margin), fill=colors[0])
            return

        bands = 4 if border in {"multi_band", "corner_resolved", ""} else 2
        for index in range(bands):
            inset = margin * index
            color = colors[index % 2]
            draw.rectangle(
                (inset, inset, width - inset - 1, height - inset - 1),
                outline=color,
                width=margin,
            )

        step = max(20, margin * 2)
        y_top = margin + margin // 2
        y_bottom = height - y_top
        for x in range(margin * 2, width - margin * 2, step):
            self._diamond(draw, x, y_top, margin // 2, colors[3], colors[1])
            self._diamond(draw, x, y_bottom, margin // 2, colors[3], colors[1])
        x_left = margin + margin // 2
        x_right = width - x_left
        for y in range(margin * 2, height - margin * 2, step):
            self._diamond(draw, x_left, y, margin // 2, colors[3], colors[1])
            self._diamond(draw, x_right, y, margin // 2, colors[3], colors[1])

    def _draw_medallion(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        colors: list[str],
        motifs: list[str],
        rng: random.Random,
    ) -> None:
        left, top, right, bottom = box
        cx, cy = (left + right) // 2, (top + bottom) // 2
        radius = int(min(right - left, bottom - top) * 0.28)
        points = self._star_points(cx, cy, radius, radius // 2, 12)
        draw.polygon(points, fill=colors[0], outline=colors[1])
        draw.line(points + [points[0]], fill=colors[3], width=max(2, radius // 18))
        self._diamond(draw, cx, cy, radius // 2, colors[1], colors[3])
        self._motif(draw, cx, cy, radius // 3, motifs[0], colors[3], colors[2])

        satellite_radius = int(radius * 1.65)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x = cx + int(math.cos(rad) * satellite_radius)
            y = cy + int(math.sin(rad) * satellite_radius)
            motif = motifs[(angle // 45) % len(motifs)]
            self._motif(draw, x, y, max(10, radius // 5), motif, colors[1], colors[3])

        for _ in range(20):
            x = rng.randint(left + radius // 3, right - radius // 3)
            y = rng.randint(top + radius // 3, bottom - radius // 3)
            if math.dist((x, y), (cx, cy)) > radius * 1.9:
                self._diamond(draw, x, y, max(4, radius // 18), colors[0], colors[3])

    def _draw_repeat(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        colors: list[str],
        motifs: list[str],
        rng: random.Random,
    ) -> None:
        left, top, right, bottom = box
        cols, rows = 7, 9
        cell_w = (right - left) / cols
        cell_h = (bottom - top) / rows
        size = int(min(cell_w, cell_h) * 0.34)
        for row in range(rows):
            for col in range(cols):
                x = int(left + (col + 0.5) * cell_w)
                y = int(top + (row + 0.5) * cell_h)
                motif = motifs[(row + col) % len(motifs)]
                fill = colors[(row + col) % 2]
                accent = colors[3] if rng.random() > 0.2 else colors[0]
                self._motif(draw, x, y, size, motif, fill, accent)

    def _draw_stripes(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        colors: list[str],
        motifs: list[str],
    ) -> None:
        left, top, right, bottom = box
        stripe_h = max(24, (bottom - top) // 9)
        for index, y in enumerate(range(top, bottom, stripe_h)):
            draw.rectangle((left, y, right, min(y + stripe_h, bottom)), fill=colors[index % 2])
            for x in range(left + stripe_h, right, stripe_h * 2):
                self._motif(
                    draw,
                    x,
                    y + stripe_h // 2,
                    stripe_h // 3,
                    motifs[index % len(motifs)],
                    colors[3],
                    colors[2],
                )

    def _draw_concentric(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        colors: list[str],
        motifs: list[str],
    ) -> None:
        left, top, right, bottom = box
        layers = 7
        step = min(right - left, bottom - top) // (layers * 2)
        for index in range(layers):
            inset = index * step
            draw.rectangle(
                (left + inset, top + inset, right - inset, bottom - inset),
                fill=colors[index % 3],
                outline=colors[3],
                width=max(2, step // 7),
            )
        self._motif(
            draw,
            (left + right) // 2,
            (top + bottom) // 2,
            step,
            motifs[0],
            colors[3],
            colors[2],
        )

    def _draw_directional(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        colors: list[str],
        motifs: list[str],
    ) -> None:
        left, top, right, bottom = box
        cx = (left + right) // 2
        step = max(35, (bottom - top) // 8)
        for index, y in enumerate(range(top + step, bottom, step)):
            size = max(12, step // 3)
            offset = step if index % 2 else 0
            for x in (cx - offset, cx + offset):
                self._motif(
                    draw,
                    x,
                    y,
                    size,
                    motifs[index % len(motifs)],
                    colors[index % 2],
                    colors[3],
                )

    def _draw_corner_accents(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        colors: list[str],
        motif: str,
    ) -> None:
        left, top, right, bottom = box
        size = max(14, min(right - left, bottom - top) // 18)
        offset = size + 8
        for x, y in (
            (left + offset, top + offset),
            (right - offset, top + offset),
            (left + offset, bottom - offset),
            (right - offset, bottom - offset),
        ):
            self._motif(draw, x, y, size, motif, colors[0], colors[3])

    def _motif(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        size: int,
        motif: str,
        fill: str,
        accent: str,
    ) -> None:
        if motif in {"star", "rosette", "palmette"}:
            points = self._star_points(x, y, size, max(3, size // 2), 8)
            draw.polygon(points, fill=fill, outline=accent)
            draw.ellipse((x - size // 4, y - size // 4, x + size // 4, y + size // 4), fill=accent)
        elif motif in {"chevron", "running_water", "vine_scroll"}:
            width = max(2, size // 5)
            draw.line(
                (x - size, y - size // 2, x, y + size // 2, x + size, y - size // 2),
                fill=fill,
                width=width,
            )
            draw.line(
                (x - size, y, x, y + size, x + size, y), fill=accent, width=max(1, width // 2)
            )
        elif motif in {"ram_horn", "hook", "elibelinde"}:
            width = max(2, size // 5)
            draw.line(
                (x, y + size, x, y - size, x - size, y - size, x - size, y), fill=fill, width=width
            )
            draw.line(
                (x, y + size, x, y - size, x + size, y - size, x + size, y), fill=fill, width=width
            )
            self._diamond(draw, x, y, size // 2, accent, fill)
        else:
            self._diamond(draw, x, y, size, fill, accent)

    def _diamond(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        size: int,
        fill: str,
        outline: str,
    ) -> None:
        draw.polygon(
            [(x, y - size), (x + size, y), (x, y + size), (x - size, y)],
            fill=fill,
            outline=outline,
        )

    def _star_points(
        self, cx: int, cy: int, outer: int, inner: int, points: int
    ) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for index in range(points * 2):
            angle = -math.pi / 2 + index * math.pi / points
            radius = outer if index % 2 == 0 else inner
            result.append((cx + int(math.cos(angle) * radius), cy + int(math.sin(angle) * radius)))
        return result

    def _add_woven_texture(self, image: Image.Image, spacing: int) -> None:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(0, image.height, spacing * 2):
            draw.line((0, y, image.width, y), fill=(255, 255, 255, 10), width=1)
        for x in range(spacing, image.width, spacing * 2):
            draw.line((x, 0, x, image.height), fill=(0, 0, 0, 8), width=1)
        image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"))
