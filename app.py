from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from io import BytesIO
import os
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "change-me"

# --- constants ---
MM_TO_PT = 72.0 / 25.4
PAGE_W = 70 * MM_TO_PT
PAGE_H = 30 * MM_TO_PT

COLOURS = {
    "AT0001": "Black",
    "AT0002": "Blue",
    "AT0003": "White",
    "AT0004": "Pink",
}

# Series allowed per SKU
SERIES_BY_SKU = {
    "AT0003": list("AEIMQUY"),  # White
    "AT0002": list("BFJNRVZ"),  # Blue
    "AT0001": list("CGKOSW"),   # Black
    "AT0004": list("DHLPTX"),   # Pink
}

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

    # Measure intrinsic module count
    tmp = code128.Code128(barcode_text, barHeight=bar_height, barWidth=1.0, humanReadable=False)
    module_count = tmp.width  # with barWidth=1pt

    # Compute width at X_MIN
    width_at_xmin = module_count * X_MIN_PT + 2 * quiet_each_side

    if width_at_xmin <= usable_w:
        bar_width = X_MIN_PT
        internal_quiet = quiet_each_side
    else:
        # Scale to fit, keep a tiny but non-zero quiet zone
        safety_quiet = max(0.1 * MM_TO_PT, 0.05 * (usable_w/2.0))
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

def validate_inputs(color_code: str, series: str, start_num: str, end_num: str):
    if color_code not in COLOURS:
        raise ValueError("Invalid colour code. Choose one of the listed AT000X values.")

    # Series must be among allowed for that SKU
    series = (series or "").strip().upper()
    allowed_for_sku = SERIES_BY_SKU[color_code]
    if series not in allowed_for_sku:
        allowed_str = ", ".join(allowed_for_sku)
        raise ValueError(f"Invalid series for {color_code}. Allowed: {allowed_str}")

    if not (start_num and end_num):
        raise ValueError("Please provide both Start and End numbers (0001–9999).")

    if len(start_num) != 4 or len(end_num) != 4 or not start_num.isdigit() or not end_num.isdigit():
        raise ValueError("Numbers must be 4 digits, e.g., 0001, 0075, 0315.")

    s = int(start_num)
    e = int(end_num)
    if not (1 <= s <= 9999 and 1 <= e <= 9999):
        raise ValueError("Numbers must be between 0001 and 9999.")
    if e < s:
        raise ValueError("End number must be greater than or equal to Start number.")

    return series, s, e

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        color_code = request.form.get("color_code", "").strip()
        series = request.form.get("series", "").strip()
        start_num = request.form.get("start_num", "").strip()
        end_num = request.form.get("end_num", "").strip()

        try:
            series, start_i, end_i = validate_inputs(color_code, series, start_num, end_num)
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("index"))

        color_name = COLOURS[color_code]

        # Create PDF in memory
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))

        for i in range(start_i, end_i + 1):
            num_str = f"{i:04d}"
            barcode_value = f"{color_code}-{series}{num_str}"
            draw_single_label(c, barcode_value, color_name)
            c.showPage()

        c.save()
        buffer.seek(0)

        filename = f"barcodes_{color_code}_{series}{start_i:04d}-{series}{end_i:04d}.pdf"
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    # Pass allowed map to template for UX hints
    return render_template("index.html", colours=COLOURS, series_by_sku=SERIES_BY_SKU)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
