# backend/agents/pan_agent.py
"""
PAN OCR agent (strict-name-from-header-crop)

RULE (highest priority):
  - NAME = first non-empty text line immediately AFTER the header containing
    "INCOME TAX DEPARTMENT" (detected by locating header bounding box and
    OCRing the region directly beneath it).

Behavior:
  - Perform full-page OCR to detect PAN and DOB.
  - Use image_to_data to find header bounding box.
  - Crop an area directly below the header, preprocess the crop, OCR it
    using single-line mode (--psm 7) to reliably obtain the NAME.
  - Fallback: if header detection fails, use strict next-line-in-text extraction.
"""
import re
import os
from datetime import datetime
from typing import Optional, Tuple

from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from pdf2image import convert_from_path
import pytesseract
from fuzzywuzzy import fuzz

from backend.database import SessionLocal
from backend.models.db_models import KYCData, Application

# Configure tesseract path if needed (Windows default)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Regexes
PAN_REGEX = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]", re.I)
PAN_LOOSE = re.compile(r"([A-Z]\s*[A-Z]\s*[A-Z]\s*[A-Z]\s*[A-Z])\s*([0-9]\s*[0-9]\s*[0-9]\s*[0-9])\s*([A-Z])", re.I)
DOB_RE = re.compile(r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{4})")


# -----------------------
# Image helpers
# -----------------------
def load_first_image(path: str) -> Image.Image:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        pages = convert_from_path(path, dpi=300)
        if not pages:
            raise RuntimeError("PDF conversion returned no pages")
        return pages[0]
    return Image.open(path)


def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Convert to grayscale, autocontrast, sharpen and upscale small images.
    """
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    if w < 1200:
        img = img.resize((int(w * 1.5), int(h * 1.5)), Image.LANCZOS)
    return img


# -----------------------
# OCR helpers
# -----------------------
def ocr_tesseract(path: str) -> Tuple[str, Image.Image]:
    """
    Return tuple (full_ocr_text, pil_image).
    Use psm 6 then psm 3 as fallback; prefer text containing PAN token.
    """
    img = load_first_image(path)
    img = preprocess_image(img)

    text6 = ""
    text3 = ""
    try:
        text6 = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
    except Exception:
        text6 = ""
    if PAN_REGEX.search(text6):
        return text6, img
    try:
        text3 = pytesseract.image_to_string(img, lang="eng", config="--psm 3")
    except Exception:
        text3 = text6
    if PAN_REGEX.search(text3) and not PAN_REGEX.search(text6):
        return text3, img
    # prefer longer non-empty text
    chosen = text3 if len(text3.strip()) > len(text6.strip()) else text6
    return chosen, img


# -----------------------
# PAN parsing & name extraction
# -----------------------
def extract_pan_from_text(ocr_text: str) -> Optional[str]:
    if not ocr_text:
        return None
    up = ocr_text.upper()
    m = PAN_REGEX.search(up)
    if m:
        return m.group(0).upper()
    m2 = PAN_LOOSE.search(up)
    if m2:
        compact = "".join(m2.groups()).replace(" ", "")
        if PAN_REGEX.fullmatch(compact):
            return compact.upper()
    toks = re.findall(r"[A-Z0-9]{8,12}", up) or []
    for t in toks:
        c = re.sub(r"[^A-Z0-9]", "", t)
        if PAN_REGEX.fullmatch(c):
            return c.upper()
    return None


def crop_and_ocr_name_region(img: Image.Image, header_left: int, header_top: int, header_right: int, header_bottom: int) -> Optional[str]:
    """
    Given header bounding box coordinates on img, crop region below it and OCR as single line.
    Return cleaned name or None.
    """
    try:
        img_w, img_h = img.size
        # Build crop bounds relative to header
        crop_top = max(0, header_bottom + int(0.01 * img_h))
        crop_bottom = min(img_h, header_bottom + int(0.22 * img_h))  # region height ~22% of image
        crop_left = max(0, header_left - int(0.02 * img_w))
        crop_right = min(img_w, header_right + int(0.55 * img_w))    # extend right to cover name area

        if crop_bottom - crop_top < 8 or crop_right - crop_left < 20:
            return None

        crop = img.crop((crop_left, crop_top, crop_right, crop_bottom))

        # aggressive preprocessing for clean single-line OCR
        crop = crop.convert("L")
        crop = ImageOps.autocontrast(crop)
        crop = ImageEnhance.Sharpness(crop).enhance(2.0)
        crop = ImageEnhance.Contrast(crop).enhance(1.4)
        w, h = crop.size
        if w < 900:
            crop = crop.resize((int(w * 1.6), int(h * 1.6)), Image.LANCZOS)
        crop = crop.filter(ImageFilter.MedianFilter(size=3))

        # single-line OCR
        name_candidate = pytesseract.image_to_string(crop, lang="eng", config="--psm 7 --oem 3")
        name_candidate = re.sub(r"[^A-Za-z\s\.\&\-\']", " ", name_candidate).strip()
        name_candidate = re.sub(r"\s+", " ", name_candidate).strip()
        if name_candidate:
            # Normalize capitalization: keep initials as uppercase
            tokens = name_candidate.split()
            norm = []
            for t in tokens:
                if len(t) == 1:
                    norm.append(t.upper())
                else:
                    norm.append(t.capitalize())
            return " ".join(norm).strip()
    except Exception:
        return None
    return None


def extract_name_and_dob_from_pan_text(ocr_text: str, img: Image.Image = None):
    """
    1) Extract DOB from full OCR text (first dd/mm/yyyy).
    2) Use image_to_data to find header words, compute header bbox, crop beneath,
       OCR that crop for NAME using crop_and_ocr_name_region.
    3) If image-based detection fails, fallback to strict next-line-in-text (line following header).
    """
    # DOB extraction and normalization
    dob = None
    dob_match = DOB_RE.search(ocr_text)
    if dob_match:
        raw_dob = dob_match.group(1)
        parts = re.split(r"[\/\-\.\s]+", raw_dob)
        if len(parts) >= 3:
            dd = parts[0].zfill(2); mm = parts[1].zfill(2); yyyy = parts[2]
            dob = f"{dd}/{mm}/{yyyy}"
        else:
            dob = raw_dob

    name = None

    # Image-based header detection + crop OCR
    if img is not None:
        try:
            data = pytesseract.image_to_data(img, lang="eng", output_type=pytesseract.Output.DICT)
            n_boxes = len(data.get('text', []))
            header_indices = []
            # Identify words that belong to header by presence of 'INCOME' or 'TAX' tokens in same nearby line
            for i in range(n_boxes):
                txt = (data['text'][i] or "").strip()
                if not txt:
                    continue
                up_txt = txt.upper()
                if "INCOME" in up_txt or "TAX" in up_txt or "INCOME TAX" in up_txt:
                    header_indices.append(i)

            if header_indices:
                # compute bounding rectangle of header tokens
                lefts = [int(data['left'][i]) for i in header_indices]
                tops = [int(data['top'][i]) for i in header_indices]
                widths = [int(data['width'][i]) for i in header_indices]
                heights = [int(data['height'][i]) for i in header_indices]

                header_left = min(lefts)
                header_top = min(tops)
                header_right = max([lefts[idx] + widths[idx] for idx in range(len(lefts))])
                header_bottom = max([tops[idx] + heights[idx] for idx in range(len(tops))])

                # try crop-and-ocr name region
                name = crop_and_ocr_name_region(img, header_left, header_top, header_right, header_bottom)
        except Exception:
            name = None

    # Fallback: strict next-line in OCR text if header present in text lines
    if not name:
        lines = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]
        header_index = None
        for idx, ln in enumerate(lines):
            if "INCOME TAX" in ln.upper() or "INCOME TAX DEPARTMENT" in ln.upper():
                header_index = idx
                break
        if header_index is not None and header_index + 1 < len(lines):
            cand = lines[header_index + 1]
            cand = re.sub(r"[^A-Za-z\s\.\&\-\']", " ", cand).strip()
            cand = re.sub(r"\s+", " ", cand)
            if cand:
                tokens = cand.split()
                norm = []
                for t in tokens:
                    if len(t) == 1:
                        norm.append(t.upper())
                    else:
                        norm.append(t.capitalize())
                name = " ".join(norm).strip()

    return {"name": name, "dob": dob}


# -----------------------
# Compare with intake
# -----------------------
def compare_with_intake(intake: Application, ocr: dict):
    failed = []
    result = {}

    # NAME - fuzzy compare (threshold 70)
    try:
        name_ok = bool(ocr.get("name")) and fuzz.ratio((intake.name or "").lower(), (ocr.get("name") or "").lower()) >= 70
    except Exception:
        name_ok = False
    result["name_match"] = bool(name_ok)
    if not name_ok:
        failed.append("name")

    # DOB - normalize and compare with intake.dob (datetime.date)
    dob_ok = False
    if ocr.get("dob") and intake.dob:
        try:
            ocr_dob_date = datetime.strptime(ocr["dob"].strip(), "%d/%m/%Y").date()
            dob_ok = (ocr_dob_date == intake.dob)
        except Exception:
            dob_ok = False
    result["dob_match"] = bool(dob_ok)
    if not dob_ok:
        failed.append("dob")

    # PAN exact compare
    ocr_pan = (ocr.get("pan") or "").replace(" ", "").upper()
    intake_pan = (getattr(intake, "pan", "") or "").replace(" ", "").upper()
    pan_ok = bool(ocr_pan and intake_pan and ocr_pan == intake_pan)
    result["pan_match"] = pan_ok
    if not pan_ok:
        failed.append("pan")

    # Final decision
    if failed:
        status = "REJECTED"
        message = "Mismatch in: " + ", ".join(failed)
    else:
        status = "APPROVED"
        message = "All fields matched"

    result["failed_fields"] = failed
    result["kyc_status"] = status
    result["message"] = message
    return result


# -----------------------
# Main PAN OCR Agent entry
# -----------------------
def run_pan_ocr_agent(app_id: int, file_path: str):
    db = SessionLocal()
    try:
        intake = db.query(Application).filter(Application.app_id == app_id).first()
        if not intake:
            return {"error": "Invalid application ID"}

        raw_text, pil_img = ocr_tesseract(file_path)

        pan = extract_pan_from_text(raw_text)
        info = extract_name_and_dob_from_pan_text(raw_text, img=pil_img)

        parsed = {
            "pan": pan,
            "name": info.get("name"),
            "dob": info.get("dob")
        }

        match = compare_with_intake(intake, parsed)

        # Save snapshot to KYCData (only set columns that exist in model)
        kyc = KYCData(
            app_id=app_id,
            extracted_name=parsed.get("name"),
            extracted_dob=parsed.get("dob"),
            extracted_aadhaar=None,
            extracted_pan=(parsed.get("pan") or "").upper().strip() if parsed.get("pan") else None,
            extracted_address=None,
            ocr_confidence=0.90,
            updated_at=datetime.now()
        )

        db.add(kyc)
        db.commit()

        return {
            "parsed": parsed,
            "match_results": match,
            "kyc_status": match["kyc_status"],
            "message": match["message"]
        }

    except Exception as e:
        db.rollback()
        return {"error": "Internal error in PAN agent", "details": str(e)}
    finally:
        db.close()
