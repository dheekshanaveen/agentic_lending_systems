import re
import os
from datetime import datetime

import pytesseract
from pdf2image import convert_from_path
from fuzzywuzzy import fuzz

from backend.database import SessionLocal
from backend.models.db_models import KYCData, Application

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        pages = convert_from_path(file_path)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p, lang="eng")
        return text

    return pytesseract.image_to_string(file_path, lang="eng")


def parse_aadhaar_text(text: str):
    aadhaar_regex = r"\b\d{4}\s\d{4}\s\d{4}\b"
    aadhaar_number = re.search(aadhaar_regex, text)
    aadhaar_number = aadhaar_number.group() if aadhaar_number else None

    dob_regex = r"\b\d{2}/\d{2}/\d{4}\b"
    dob = re.search(dob_regex, text)
    dob = dob.group() if dob else None

    # name → line above DOB
    lines = text.split("\n")
    name = None
    if dob:
        for i, line in enumerate(lines):
            if dob in line and i > 0:
                name = lines[i - 1].strip()
                break

    # Address
    address = ""
    if "Address" in text:
        start = text.index("Address")
        address = text[start:].replace("Address", "").strip()
        address = " ".join(address.split("\n")[:6])

    return {
        "name": name,
        "dob": dob,
        "address": address,
        "aadhaar_number": aadhaar_number,
    }


def compare_with_intake(intake, ocr):
    results = {
        "name_match": False,
        "dob_match": False,
        "aadhaar_match": False,
        "address_match": False
    }

    # Name fuzzy (70%)
    if intake.name and ocr["name"]:
        if fuzz.ratio(intake.name.lower(), ocr["name"].lower()) >= 70:
            results["name_match"] = True

    # DOB exact dd/mm/yyyy
    if intake.dob and ocr["dob"]:
        if intake.dob.strftime("%d/%m/%Y") == ocr["dob"]:
            results["dob_match"] = True

    # Aadhaar number
    if ocr["aadhaar_number"]:
        if intake.pan == ocr["aadhaar_number"]:  
            results["aadhaar_match"] = True

    # Address partial fuzzy (60%)
    if intake.address and ocr["address"]:
        if fuzz.partial_ratio(intake.address.lower(), ocr["address"].lower()) >= 60:
            results["address_match"] = True

    return results


def process_aadhar_ocr(app_id: int, document):
    db = SessionLocal()

    intake = db.query(Application).filter(Application.app_id == app_id).first()

    if not intake:
        db.close()
        return {"error": "Invalid application ID"}

    # save temp file
    file_path = f"temp_aadhar_{app_id}.jpg"
    with open(file_path, "wb") as f:
        f.write(document.file.read())

    # Step 1 extract text
    raw_text = extract_text(file_path)

    # Step 2 parse
    parsed = parse_aadhaar_text(raw_text)

    # Step 3 compare
    match_results = compare_with_intake(intake, parsed)

    # Step 4 store
    kyc = KYCData(
        app_id=app_id,
        extracted_name=parsed["name"],
        extracted_dob=parsed["dob"],
        extracted_pan=parsed["aadhaar_number"],
        extracted_address=parsed["address"],
        ocr_confidence=0.9,
        updated_at=datetime.now()
    )
    db.add(kyc)
    db.commit()
    db.close()

    return {
        "parsed": parsed,
        "match_results": match_results,
        "ocr_status": "AADHAAR_CHECK_COMPLETE"
    }
