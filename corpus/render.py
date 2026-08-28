#!/usr/bin/env python3
"""Render the corpus sources to the PDFs the pipeline actually ingests.

The Markdown files under `documents/` are the source of truth: reviewable,
diffable, and easy to correct when the ground-truth map disagrees with them.
The PDFs are build artefacts. Regenerate with:

    docker compose exec api python /corpus/render.py

Three render modes, driven by the `render:` key in each file's frontmatter:

  clean       Digital-native text. Extractable text layer, no OCR needed.
  degraded    The same text rasterised, skewed, blurred and speckled to
              approximate a fax or a poor scan. No text layer — OCR must read
              it. Used to produce the second copy of the discharge summary.
  handwritten Per-character jitter, rotation and baseline wobble over a
              degraded background.

A note on the handwriting mode: this is a *simulation of the OCR failure*, not
real handwriting. It reliably produces the low-confidence output that should
trigger manual-only routing, which is the behaviour under test. It does not
exercise a real handwriting recogniser, and the corpus README says so.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent
SOURCES = ROOT / "documents"
OUT = ROOT / "rendered"

PAGE_W, PAGE_H = pymupdf.paper_size("a4")
MARGIN = 56
LEADING = 13.2
FONT_SIZE = 9.5
FOOTER = "SYNTHETIC TEST DOCUMENT — NOT A REAL PATIENT RECORD"

# Deterministic: the same sources must produce byte-identical artefacts, or the
# evaluation harness measures render noise instead of detector behaviour.
SEED = 20260314


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Minimal frontmatter parser — avoids a PyYAML dependency for four keys."""
    if not text.startswith("---\n"):
        return {}, text
    _, raw, body = text.split("---\n", 2)
    meta: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and key:  # folded block continuation
            meta[key] = f"{meta[key]} {line.strip()}".strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            meta[key] = value.strip().lstrip(">").strip()
    return meta, body.lstrip("\n")


def draw_footer(page: pymupdf.Page) -> None:
    page.insert_text(
        (MARGIN, PAGE_H - 30), FOOTER, fontsize=6.5, fontname="helv", color=(0.45,) * 3
    )


def render_clean(lines: list[str], out_path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN
    for line in lines:
        if y > PAGE_H - MARGIN:
            draw_footer(page)
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            y = MARGIN
        page.insert_text((MARGIN, y), line, fontsize=FONT_SIZE, fontname="cour")
        y += LEADING
    draw_footer(page)
    doc.save(out_path)
    doc.close()


def _degrade(img: Image.Image, rng: random.Random, *, severity: float) -> Image.Image:
    """Skew, blur and speckle a page image into something OCR must work for."""
    img = img.rotate(
        rng.uniform(-0.9, 0.9) * severity, expand=False, fillcolor=255, resample=Image.BICUBIC
    )
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6 * severity))

    px = img.load()
    w, h = img.size
    speckles = int(w * h * 0.0035 * severity)
    for _ in range(speckles):
        x, y = rng.randrange(w), rng.randrange(h)
        px[x, y] = 0 if px[x, y] > 128 else 255

    # Horizontal banding, the way a fax drops scan lines.
    draw = ImageDraw.Draw(img)
    for _ in range(int(6 * severity)):
        y = rng.randrange(h)
        draw.line([(0, y), (w, y)], fill=rng.choice([210, 225]), width=1)

    return img.point(lambda v: 0 if v < 118 else 255)


def _image_page(img: Image.Image, out_path: Path) -> None:
    """Wrap a page image in a PDF with no text layer, so OCR is mandatory."""
    tmp = out_path.with_suffix(".tmp.png")
    img.save(tmp)
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.insert_image(pymupdf.Rect(0, 0, PAGE_W, PAGE_H), filename=str(tmp))
    doc.save(out_path)
    doc.close()
    tmp.unlink()


def render_degraded(lines: list[str], out_path: Path, rng: random.Random) -> None:
    scratch = out_path.with_suffix(".scratch.pdf")
    render_clean(lines, scratch)
    src = pymupdf.open(scratch)
    # 150 dpi: enough that OCR is plausible, low enough that degradation bites.
    pix = src[0].get_pixmap(dpi=150)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    src.close()
    scratch.unlink()
    _image_page(_degrade(img, rng, severity=1.0), out_path)


def render_handwritten(lines: list[str], out_path: Path, rng: random.Random) -> None:
    scale = 2
    img = Image.new("L", (int(PAGE_W * scale), int(PAGE_H * scale)), 255)
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    y = MARGIN + 10
    for line in lines:
        x = MARGIN + rng.uniform(-3, 3)
        baseline = y
        for ch in line:
            if ch == " ":
                x += FONT_SIZE * 0.55
                continue
            # Per-character wobble: rotation, size and baseline all drift, which
            # is what breaks the uniform-glyph assumption OCR leans on.
            page.insert_text(
                (x, baseline + rng.uniform(-1.6, 1.6)),
                ch,
                fontsize=FONT_SIZE * rng.uniform(1.15, 1.45),
                fontname="tiit",
                rotate=0,
                morph=(
                    pymupdf.Point(x, baseline),
                    pymupdf.Matrix(1, 0, math.tan(math.radians(rng.uniform(-11, 4))), 1, 0, 0),
                ),
            )
            x += FONT_SIZE * rng.uniform(0.62, 0.86)
        y += LEADING * 1.9
    draw_footer(page)

    scratch = out_path.with_suffix(".scratch.pdf")
    doc.save(scratch)
    doc.close()

    src = pymupdf.open(scratch)
    pix = src[0].get_pixmap(dpi=150)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    src.close()
    scratch.unlink()
    _image_page(_degrade(img, rng, severity=0.7), out_path)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rendered = []

    for source in sorted(SOURCES.glob("*.md")):
        meta, body = parse_frontmatter(source.read_text())
        lines = body.rstrip().splitlines()
        mode = meta.get("render", "clean")
        rng = random.Random(f"{SEED}-{source.name}")

        target = OUT / f"{source.stem}.pdf"
        if mode == "clean":
            render_clean(lines, target)
        elif mode == "degraded":
            render_degraded(lines, target, rng)
        elif mode == "handwritten":
            render_handwritten(lines, target, rng)
        else:
            raise SystemExit(f"{source.name}: unknown render mode {mode!r}")
        rendered.append((target, mode))

        # The discharge summary ships twice: identical text, different quality.
        # This is the consistency case, so it is generated from one source
        # rather than maintained as two files that could drift apart.
        if source.stem.startswith("06-discharge-summary"):
            variant = OUT / f"{source.stem}-b-degraded.pdf"
            render_degraded(lines, variant, random.Random(f"{SEED}-degraded"))
            rendered.append((variant, "degraded"))

    for path, mode in rendered:
        print(f"  {mode:12} {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")
    print(f"\n{len(rendered)} pages rendered to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
