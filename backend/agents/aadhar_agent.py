import re
import os
from datetime import datetime

import pytesseract
from pdf2image import convert_from_path
from fuzzywuzzy import fuzz

from backend.database import SessionLocal
from backend.models.db_models import KYCData, Application


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -------- DOB Extractor --------
def extract_dob(lines):
    dob_pattern = r"\b\d{2}/\d{2}/\d{4}\b"
    for line in lines:
        L = line.upper()
        if "DOB" in L or "DATE OF BIRTH" in L:
            m = re.search(dob_pattern, line)
            if m:
                return m.group()
    return None


# -------- Name Extractor --------
def extract_name(lines, dob):
    if not dob:
        return None

    name_pattern = r"^[A-Za-z][A-Za-z\s\.]{2,}$"

    for i, line in enumerate(lines):
        if dob in line:
            positions = [i-2, i-1, i+1, i+2]
            for p in positions:
                if 0 <= p < len(lines):
                    cand = lines[p].strip()
                    if re.fullmatch(name_pattern, cand):
                        return cand
    return None


# -------- Text Extraction --------
def extract_text(file_path: str) -> str:
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
    lines = text.split("\n")

    aadhaar_regex = r"\b\d{4}\s\d{4}\s\d{4}\b"
    a_match = re.search(aadhaar_regex, text)
    aadhaar = a_match.group() if a_match else None

    dob = extract_dob(lines)
    name = extract_name(lines, dob)

    address = ""
    if "Address" in text:
        start = text.index("Address")
        block = text[start:].replace("Address", "").strip()
        address = " ".join(block.split("\n")[:6])

    return {
        "name": name,
        "dob": dob,
        "address": address,
        "aadhaar_number": aadhaar
    }


# -------- Compare --------
def compare_with_intake(intake, ocr):
    failed = []
    result = {}

    # Name
    if ocr["name"] and fuzz.ratio(intake.name.lower(), ocr["name"].lower()) >= 70:
        result["name_match"] = True
    else:
        result["name_match"] = False
        failed.append("name")

    # DOB
    if ocr["dob"] == intake.dob.strftime("%d/%m/%Y"):
        result["dob_match"] = True
    else:
        result["dob_match"] = False
        failed.append("dob")

    # Aadhaar
    if (ocr["aadhaar_number"] or "").replace(" ", "") == (intake.aadhaar_number or "").replace(" ", ""):
        result["aadhaar_match"] = True
    else:
        result["aadhaar_match"] = False
        failed.append("aadhaar_number")

    # Address
    if fuzz.partial_ratio(intake.address.lower(), (ocr["address"] or "").lower()) >= 60:
        result["address_match"] = True
    else:
        result["address_match"] = False
        failed.append("address")

    if failed:
        status = "REJECTED"
        message = "Mismatch in " + ", ".join(failed)
    else:
        status = "APPROVED"
        message = "All fields matched"

    result["failed_fields"] = failed
    result["kyc_status"] = status
    result["message"] = message

    return result


# -------- Main Aadhaar OCR Agent --------
def run_aadhaar_ocr_agent(app_id: int, file_path: str):
    db = SessionLocal()

    intake = db.query(Application).filter(Application.app_id == app_id).first()
    if not intake:
        return {"error": "Invalid application ID"}

    raw = extract_text(file_path)
    parsed = parse_aadhaar_text(raw)
    match = compare_with_intake(intake, parsed)

    kyc = KYCData(
        app_id=app_id,
        extracted_name=parsed["name"],
        extracted_dob=parsed["dob"],
        extracted_aadhaar=parsed["aadhaar_number"],
        extracted_address=parsed["address"],
        ocr_confidence=0.9,
        updated_at=datetime.now()
    )

    db.add(kyc)
    db.commit()
    db.close()

    return {
        "parsed": parsed,
        "match_results": match,
        "kyc_status": match["kyc_status"],
        "message": match["message"]
    }
