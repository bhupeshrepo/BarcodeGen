# make_barcodes.py
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib import colors

# --- constants ---
MM_TO_PT = 72.0 / 25.4
PAGE_W = 70 * MM_TO_PT
PAGE_H = 30 * MM_TO_PT

COLOURS = {"AT0004": "Pink"}  # just what we need
COLOR_CODE = "AT0004"
COLOR_NAME = COLOURS[COLOR_CODE]
SERIES = "D"  # Pink (D), blue (b), white(a)

# Your old numbers (kept as-is, including duplicates)
NUMBERS = [310, 315, 311, 229, 309, 313, 162, 302, 183, 304, 308, 301, 196, 131, 199, 303, 206, 192, 130, 173, 305, 227, 178, 198, 195, 215, 191, 200, 184, 186, 174, 181, 146, 187, 189, 175, 185, 180, 197, 194]

def draw_single_label(c: canvas.Canvas, barcode_text: str, color_name: str):
    # Physical margins (outside quiet zones)
    outer_margin_mm = 1.0
    left_margin   = outer_margin_mm * MM_TO_PT
    right_margin  = outer_margin_mm * MM_TO_PT
    top_margin    = 1.0 * MM_TO_PT
    bottom_margin = 1.0 * MM_TO_PT

    # Human-readable text band
    font_name = "Helvetica"
    font_size = 8
    gap_above_text = 0.8 * MM_TO_PT
    text_band_h = font_size + gap_above_text

    usable_w = PAGE_W - left_margin - right_margin
    usable_h = PAGE_H - top_margin - bottom_margin - text_band_h

    # --- Barcode sizing rules ---
    X_MIN_MM = 0.30  # ~12 mil
    X_MIN_PT = X_MIN_MM * MM_TO_PT

    # Quiet zone: ≥ 10X on each side; also enforce ≥2mm
    QUIET_X_MULT = 10
    quiet_each_side = max(QUIET_X_MULT * X_MIN_PT, 2.0 * MM_TO_PT)

    # Desired bar height
    BAR_HEIGHT_MM = 14
    bar_height = min(usable_h, BAR_HEIGHT_MM * MM_TO_PT)

    # Measure intrinsic module count at 1pt
    tmp = code128.Code128(barcode_text, barHeight=bar_height, barWidth=1.0, humanReadable=False)
    module_count = tmp.width  # with barWidth=1pt

    # Compute width at X_MIN
    width_at_xmin = module_count * X_MIN_PT + 2 * quiet_each_side

    if width_at_xmin <= usable_w:
        bar_width = X_MIN_PT
        internal_quiet = quiet_each_side
    else:
        # Scale to fit, keep a tiny but non-zero quiet zone
        safety_quiet = max(0.1 * MM_TO_PT, 0.05 * (usable_w / 2.0))
        available_for_bars = max(usable_w - 2 * safety_quiet, 1)
        bar_width = available_for_bars / module_count
        internal_quiet = safety_quiet

    # Build final barcode
    bc = code128.Code128(
        barcode_text,
        barHeight=bar_height,
        barWidth=bar_width,
        humanReadable=False,
    )

    # Positioning
    x = left_margin + internal_quiet
    y = bottom_margin + text_band_h + (usable_h - bar_height) / 2.0
    bc.drawOn(c, x, y)

    # Text line
    label_text = f"{barcode_text} | {color_name}"
    c.setFillColor(colors.black)
    c.setFont(font_name, font_size)
    text_w = c.stringWidth(label_text, font_name, font_size)
    c.drawString((PAGE_W - text_w) / 2.0, bottom_margin, label_text)

def main():
    filename = "barcodes_AT0004_D_list.pdf"
    c = canvas.Canvas(filename, pagesize=(PAGE_W, PAGE_H))

    for n in NUMBERS:
        if not (1 <= int(n) <= 9999):
            # Skip anything out of bounds (shouldn't happen with your list)
            continue
        num_str = f"{int(n):04d}"
        barcode_value = f"{COLOR_CODE}-{SERIES}{num_str}"   # e.g., AT0004-D0222
        draw_single_label(c, barcode_value, COLOR_NAME)
        c.showPage()

    c.save()
    print(f"✔ PDF written: {filename}")

if __name__ == "__main__":
    main()
