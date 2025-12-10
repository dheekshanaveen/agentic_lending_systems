import re
import os
from datetime import datetime

import pytesseract
from pdf2image import convert_from_path
from fuzzywuzzy import fuzz

from backend.database import SessionLocal
from backend.models.db_models import KYCData, Application

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -------------------------------------------------------
# SMART NAME EXTRACTOR (MUCH BETTER)
# -------------------------------------------------------
def extract_name(lines, dob):
    """
    Extract name by:
    1. Finding DOB line
    2. Searching above & below for ENGLISH FULL NAME
    """

    name_pattern = r"^[A-Za-z][A-Za-z\s\.]{2,}$"  # clean English name

    for i, line in enumerate(lines):
        if dob in line:

            search_block = []

            # check 3 lines above & 3 lines below DOB
            positions = [i - 2, i - 1, i, i + 1, i + 2]

            for p in positions:
                if 0 <= p < len(lines):
                    search_block.append(lines[p].strip())

            # return first valid English name
            for text in search_block:
                if re.fullmatch(name_pattern, text):
                    return text

    return None


# -------------------------------------------------------
# TEXT EXTRACTION
# -------------------------------------------------------
def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        pages = convert_from_path(file_path)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p, lang="eng")
        return text

    return pytesseract.image_to_string(file_path, lang="eng")


# -------------------------------------------------------
# AADHAAR PARSER
# -------------------------------------------------------
def parse_aadhaar_text(text: str):
    # Aadhaar number
    aadhaar_regex = r"\b\d{4}\s\d{4}\s\d{4}\b"
    aadhaar_number = re.search(aadhaar_regex, text)
    aadhaar_number = aadhaar_number.group() if aadhaar_number else None

    # DOB
    dob_regex = r"\b\d{2}/\d{2}/\d{4}\b"
    dob = re.search(dob_regex, text)
    dob = dob.group() if dob else None

    lines = text.split("\n")

    # SMART NAME EXTRACTION
    name = extract_name(lines, dob)

    # Address extraction
    address = ""
    if "Address" in text:
        start = text.index("Address")
        address_block = text[start:].replace("Address", "").strip()
        address = " ".join(address_block.split("\n")[:6])

    return {
        "name": name,
        "dob": dob,
        "address": address,
        "aadhaar_number": aadhaar_number,
    }


# -------------------------------------------------------
# MATCH WITH INTAKE + FAIL REASONS
# -------------------------------------------------------
def compare_with_intake(intake, ocr):
    results = {}
    failed = []

    # NAME
    if ocr["name"] and fuzz.ratio(intake.name.lower(), ocr["name"].lower()) >= 70:
        results["name_match"] = True
    else:
        results["name_match"] = False
        failed.append("name")

    # DOB
    if ocr["dob"] == intake.dob.strftime("%d/%m/%Y"):
        results["dob_match"] = True
    else:
        results["dob_match"] = False
        failed.append("dob")

    # AADHAAR
    if ocr["aadhaar_number"] == intake.pan:
        results["aadhaar_match"] = True
    else:
        results["aadhaar_match"] = False
        failed.append("aadhaar")

    # ADDRESS
    if fuzz.partial_ratio(intake.address.lower(), ocr["address"].lower()) >= 60:
        results["address_match"] = True
    else:
        results["address_match"] = False
        failed.append("address")

    # Final KYC status
    results["failed_fields"] = failed
    results["kyc_status"] = "APPROVED" if len(failed) == 0 else "REJECTED"

    return results


# -------------------------------------------------------
# MAIN AGENT
# -------------------------------------------------------
def run_aadhaar_ocr_agent(app_id: int, file_path: str):
    db = SessionLocal()
    intake = db.query(Application).filter(Application.app_id == app_id).first()

    if not intake:
        db.close()
        return {"error": "Invalid application ID"}

    # Extract text
    raw_text = extract_text(file_path)

    # Parse
    parsed = parse_aadhaar_text(raw_text)

    # Compare
    match_results = compare_with_intake(intake, parsed)

    # Save in DB
    kyc = KYCData(
        app_id=app_id,
        extracted_name=parsed["name"],
        extracted_dob=parsed["dob"],
        extracted_pan=parsed["aadhaar_number"],
        extracted_address=parsed["address"],
        ocr_confidence=0.9,
        updated_at=datetime.now(),
    )
    db.add(kyc)
    db.commit()
    db.close()

    return {
        "parsed": parsed,
        "match_results": match_results,
        "kyc_status": match_results["kyc_status"]
    }
