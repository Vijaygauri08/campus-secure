"""ANPR core: preprocessing, contour-based plate localisation, OCR, Indian-format correction."""
import re
import cv2
import numpy as np
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Indian plate: 2 letters (state) + 2 digits (RTO) + 1-3 letters (series) + 4 digits
PLATE_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$")
TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6"}
TO_ALPHA = {v: k for k, v in {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6"}.items()}


def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)       # denoise, keep edges
    edges = cv2.Canny(gray, 30, 200)
    return gray, edges


def locate_plate(img):
    """Return (x, y, w, h) of the most plate-like 4-sided contour, or None."""
    _, edges = preprocess(img)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        approx = cv2.approxPolyDP(c, 0.018 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            if 2.0 <= w / float(h) <= 6.0 and w > 80:
                return x, y, w, h
    return None


def read_text(img, box):
    x, y, w, h = box
    crop = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
    crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, crop = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cfg = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return re.sub(r"[^A-Z0-9]", "", pytesseract.image_to_string(crop, config=cfg).upper())


def correct_format(raw):
    """Fix typical OCR confusions (O/0, I/1...) using the plate's letter/digit positions."""
    n = len(raw)
    if n not in (9, 10, 11):
        return raw
    out = []
    for i, ch in enumerate(raw):
        want_digit = i in (2, 3) or i >= n - 4
        if want_digit:
            out.append(TO_DIGIT.get(ch, ch))
        else:
            out.append(TO_ALPHA.get(ch, ch))
    return "".join(out)


def is_valid(plate):
    return bool(PLATE_RE.match(plate))


def detect_and_read(img):
    """Full pipeline. Returns dict with plate, raw, valid, box, annotated image."""
    box = locate_plate(img)
    annotated = img.copy()
    if box is None:
        return {"plate": "", "raw": "", "valid": False, "box": None, "annotated": annotated}
    raw = read_text(img, box)
    plate = correct_format(raw)
    x, y, w, h = box
    colour = (0, 200, 0) if is_valid(plate) else (0, 165, 255)
    cv2.rectangle(annotated, (x, y), (x + w, y + h), colour, 3)
    cv2.putText(annotated, plate, (x, max(y - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, colour, 2)
    return {"plate": plate, "raw": raw, "valid": is_valid(plate), "box": box, "annotated": annotated}
