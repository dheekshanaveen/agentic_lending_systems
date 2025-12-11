# backend/agents/aadhar_agent.py
import re
import os
from datetime import datetime

import pytesseract
from pdf2image import convert_from_path
from fuzzywuzzy import fuzz

from backend.database import SessionLocal
from backend.models.db_models import KYCData, Application

# If you installed Tesseract in the default path on Windows, keep this.
# Change if your tesseract executable is elsewhere.
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -------- DOB Extractor --------
def extract_dob(lines):
    """
    Find DOB line by searching for "DOB" or "DATE OF BIRTH" and a DD/MM/YYYY pattern.
    Returns tuple (dob_str, index) where dob_str is like "12/11/2006".
    """
    dob_pattern = r"\b\d{2}/\d{2}/\d{4}\b"
    for i, line in enumerate(lines):
        upper = line.upper()
        if "DOB" in upper or "DATE OF BIRTH" in upper:
            m = re.search(dob_pattern, line)
            if m:
                return m.group(), i
    return None, None


# -------- Name Extractor (STRICT: EXACTLY ONE LINE ABOVE DOB) --------
def extract_name_strict(lines, dob_index):
    """
    Return the line exactly one above DOB if it looks like an English name.
    """
    if dob_index is None or dob_index <= 0:
        return None

    possible_name = lines[dob_index - 1].strip()

    # allow letters, spaces and dots; minimum length 3
    if re.fullmatch(r"[A-Za-z\s\.]{3,}", possible_name):
        return possible_name

    return None


# -------- Text Extraction --------
def extract_text(file_path: str) -> str:
    """
    Extract text from image or PDF. For PDF, convert pages to images then OCR.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        pages = convert_from_path(file_path)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p, lang="eng")
        return text

    return pytesseract.image_to_string(file_path, lang="eng")


# -------- Aadhaar Parser --------
def parse_aadhaar_text(text: str):
    """
    Parse Aadhaar fields from raw OCR text.
    Returns a dict with keys: name, dob (DD/MM/YYYY or None), address, aadhaar_number
    """
    lines = text.split("\n")

    # Aadhaar number (pattern 4-4-4)
    aadhaar_regex = r"\b\d{4}\s\d{4}\s\d{4}\b"
    match = re.search(aadhaar_regex, text)
    aadhaar = match.group() if match else None

    # DOB and its index
    dob, dob_index = extract_dob(lines)

    # Strict name extraction: one line above DOB
    name = extract_name_strict(lines, dob_index)

    # Address: case-insensitive search for word "Address"
    address = ""
    addr_match = re.search(r"(?i)address", text)
    if addr_match:
        start = addr_match.start()
        block = text[start:].replace("Address", "").replace("address", "").strip()
        # join first few lines into single-line address
        address = " ".join(block.split("\n")[:6]).strip()

    return {
        "name": name,
        "dob": dob,
        "address": address,
        "aadhaar_number": aadhaar
    }


# -------- Comparison --------
def compare_with_intake(intake, ocr):
    """
    Compare intake record (Application) with OCR result dict.
    intake.dob is a datetime.date. OCR dob is expected DD/MM/YYYY.
    """
    failed = []
    result = {}

    # NAME
    if ocr.get("name") and intake.name:
        try:
            name_ok = fuzz.ratio(intake.name.lower(), ocr["name"].lower()) >= 70
        except Exception:
            name_ok = False
    else:
        name_ok = False

    result["name_match"] = bool(name_ok)
    if not name_ok:
        failed.append("name")

    # DOB: normalize OCR DD/MM/YYYY -> datetime.date and compare with intake.dob
    dob_match = False
    if ocr.get("dob") and intake.dob:
        try:
            ocr_dob_date = datetime.strptime(ocr["dob"].strip(), "%d/%m/%Y").date()
            dob_match = (ocr_dob_date == intake.dob)
        except Exception:
            dob_match = False

    result["dob_match"] = bool(dob_match)
    if not dob_match:
        failed.append("dob")

    # AADHAAR NUMBER
    ocr_aadhaar = (ocr.get("aadhaar_number") or "").replace(" ", "")
    intake_aadhaar = (intake.aadhaar or "").replace(" ", "")
    if ocr_aadhaar and intake_aadhaar and ocr_aadhaar == intake_aadhaar:
        result["aadhaar_match"] = True
    else:
        result["aadhaar_match"] = False
        failed.append("aadhaar_number")

    # ADDRESS (partial fuzzy compare)
    try:
        addr_ok = fuzz.partial_ratio((intake.address or "").lower(), (ocr.get("address") or "").lower()) >= 60
    except Exception:
        addr_ok = False

    result["address_match"] = bool(addr_ok)
    if not addr_ok:
        failed.append("address")

    # FINAL DECISION
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


# -------- Main Aadhaar OCR Agent --------
def run_aadhaar_ocr_agent(app_id: int, file_path: str):
    """
    Entry point for the Aadhaar OCR agent.
    Returns parsed data and match results.
    """
    db = SessionLocal()
    try:
        intake = db.query(Application).filter(Application.app_id == app_id).first()

        if not intake:
            return {"error": "Invalid application ID"}

        raw = extract_text(file_path)
        parsed = parse_aadhaar_text(raw)
        match = compare_with_intake(intake, parsed)

        # Save OCR snapshot (store original OCR strings)
        kyc = KYCData(
            app_id=app_id,
            extracted_name=parsed.get("name"),
            extracted_dob=parsed.get("dob"),
            extracted_aadhaar=parsed.get("aadhaar_number"),
            extracted_address=parsed.get("address"),
            ocr_confidence=0.9,
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
        # Return error info (useful for development). In production return sanitized msg.
        return {"error": "Internal error in Aadhaar agent", "details": str(e)}
    finally:
        db.close()
