"""Is the thumbprint whole and clear? Checked on this server before an AS608 image is saved.

The image is split into 16x16 blocks. A block shows ridges when its brightness varies enough
(standard deviation); coverage is the share of such blocks. A partial or lightly pressed thumb
covers little of the scanner, a thumb at the edge sits off-centre, and a wet or pressed thumb is dark.
"""
from django.conf import settings

REJECTED = "Thumbprint not accepted"  # start of every rejection message (used to count retries)
BLOCK = 16
RIDGE_STD = 15        # a block with ridges varies at least this much (0-255 scale)
DARK_MEAN = 60        # a block darker than this is smudged (wet thumb or pressed too hard)
DARK_SHARE = 0.35     # more dark blocks than this: too dark
OFF_CENTRE = 0.17     # ridge centre further than this (share of width/height) from the middle
                      # (a whole AS608 thumbprint measured about 0.04-0.10; a partial one 0.26)


def assess(image):
    """{"ok", "coverage", "message"} for a grayscale PIL image. Never raises."""
    try:
        import numpy

        pixels = numpy.asarray(image.convert("L"), dtype=numpy.float32)
        rows, cols = pixels.shape[0] // BLOCK, pixels.shape[1] // BLOCK
        if rows < 4 or cols < 4:
            return {"ok": False, "coverage": 0,
                    "message": f"{REJECTED}: the image is too small. Capture again."}
        blocks = pixels[:rows * BLOCK, :cols * BLOCK].reshape(rows, BLOCK, cols, BLOCK).swapaxes(1, 2)
        spread, brightness = blocks.std(axis=(2, 3)), blocks.mean(axis=(2, 3))
        ridges = spread >= RIDGE_STD
        coverage = round(float(ridges.mean()) * 100)
    except Exception:  # an unexpected image must never stop the capture: the officer still sees it
        return {"ok": True, "coverage": None, "message": ""}

    if float((brightness < DARK_MEAN).mean()) > DARK_SHARE:
        return {"ok": False, "coverage": coverage, "message": (
            f"{REJECTED}: the image is too dark (wet thumb or pressed too hard). "
            "Wipe and dry the thumb, press gently, then capture again.")}
    if coverage < settings.FINGERPRINT_MIN_COVERAGE:
        return {"ok": False, "coverage": coverage, "message": (
            f"{REJECTED}: partial thumbprint, only {coverage}% of the scanner shows ridges. "
            "Place the whole thumb flat in the center of the scanner and press firmly, then capture again.")}
    found_rows, found_cols = numpy.nonzero(ridges)
    if (abs(found_rows.mean() / rows - 0.5) > OFF_CENTRE or abs(found_cols.mean() / cols - 0.5) > OFF_CENTRE):
        return {"ok": False, "coverage": coverage, "message": (
            f"{REJECTED}: the thumb is too close to the edge of the scanner. "
            "Place it in the center of the scanner, then capture again.")}
    return {"ok": True, "coverage": coverage, "message": f"Thumbprint accepted (coverage {coverage}%)."}
