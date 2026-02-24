"""Inspect a PDF to find dates that standard text extraction misses."""

import re
import sys
from typing import Optional

import pdfplumber


def inspect_pdf(pdf_path: str) -> None:
    """Try multiple strategies to extract dates from the PDF."""

    with pdfplumber.open(pdf_path) as pdf:
        # --- 1. Metadata (pikepdf/pdfplumber decrypt automatically) ---
        meta = pdf.metadata or {}
        print("=== PDF Metadata ===")
        for key, val in meta.items():
            print(f"  {key}: {val}")

        print(f"\n=== PDF has {len(pdf.pages)} pages ===")

        for i, page in enumerate(pdf.pages[:3]):
            print(f"\n{'='*60}")
            print(f"PAGE {i + 1}  (w={page.width}, h={page.height})")
            print(f"{'='*60}")

            # --- 2. Standard text extraction ---
            print(f"\n--- Standard extract_text() ---")
            text = page.extract_text() or "(empty)"
            print(text[:2000])

            # --- 3. Layout-mode text extraction ---
            print(f"\n--- extract_text(layout=True) ---")
            try:
                text_layout = page.extract_text(layout=True) or "(empty)"
                print(text_layout[:2000])
            except Exception as e:
                print(f"  (layout mode failed: {e})")

            # --- 4. All words with position + font info ---
            print(f"\n--- All Words (with position/font) ---")
            words = page.extract_words(
                keep_blank_chars=True,
                extra_attrs=["fontname", "size"],
            )
            print(f"  Total words: {len(words)}")
            for w in words[:100]:
                print(f"  x0={w['x0']:6.1f}  top={w['top']:6.1f}  "
                      f"font={w.get('fontname',''):20s}  "
                      f"size={w.get('size',''):5}  "
                      f"text='{w['text']}'")

            # --- 5. Individual characters (most granular) ---
            print(f"\n--- Individual Characters (first 200) ---")
            chars = page.chars
            print(f"  Total chars: {len(chars)}")
            for c in chars[:200]:
                print(f"  x0={c['x0']:6.1f}  top={c['top']:6.1f}  "
                      f"font={c.get('fontname',''):20s}  "
                      f"size={c.get('size',''):5}  "
                      f"char='{c['text']}'  "
                      f"adv={c.get('adv', '')}")

            # --- 6. Search for date-like patterns in chars ---
            print(f"\n--- Searching for month names / date digits in chars ---")
            all_char_text = "".join(c["text"] for c in chars)
            print(f"  All chars joined ({len(all_char_text)} chars):")
            print(f"  {all_char_text[:500]}")

            # Look for month names
            month_re = re.compile(
                r'(January|February|March|April|May|June|July|August|'
                r'September|October|November|December|'
                r'through|THROUGH)',
                re.IGNORECASE,
            )
            matches = list(month_re.finditer(all_char_text))
            if matches:
                for m in matches:
                    ctx_start = max(0, m.start() - 20)
                    ctx_end = min(len(all_char_text), m.end() + 40)
                    print(f"  FOUND '{m.group()}' at pos {m.start()}: "
                          f"...{all_char_text[ctx_start:ctx_end]}...")
            else:
                print("  (no month names found in chars)")

            # --- 7. Cropped regions ---
            for crop_height in (80, 120, 200):
                print(f"\n--- Cropped top {crop_height}pt ---")
                cropped = page.crop((0, 0, page.width, crop_height))
                ct = cropped.extract_text() or "(empty)"
                print(ct)

            # Also try right side of header
            print(f"\n--- Cropped top-right quadrant (top 150pt, right half) ---")
            cropped = page.crop((page.width / 2, 0, page.width, 150))
            ct = cropped.extract_text() or "(empty)"
            print(ct)

        # --- 8. Check for images on page 1 (date might be rasterized) ---
        print(f"\n{'='*60}")
        print("=== Images on page 1 ===")
        page = pdf.pages[0]
        images = page.images
        print(f"  Found {len(images)} image(s)")
        for idx, img in enumerate(images[:10]):
            print(f"  Image {idx}: x0={img['x0']:.0f} top={img['top']:.0f} "
                  f"x1={img['x1']:.0f} bottom={img['bottom']:.0f} "
                  f"width={img['x1']-img['x0']:.0f} "
                  f"height={img['bottom']-img['top']:.0f}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "statement.pdf"
    inspect_pdf(path)
