import re
import pytesseract
from pdf2image import convert_from_path
from backend.database import SessionLocal
from backend.models.db_models import KYCData
from datetime import datetime

pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"


def extract_text_from_file(path):
    if path.lower().endswith(".pdf"):
        pages = convert_from_path(path)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page)
        return text

    else:
        return pytesseract.image_to_string(path)


def extract_name(text):
    m = re.search(r"Name\s*:?\s*([A-Za-z ]+)", text)
    if m: return m.group(1).strip()

    # fallback: name appears above DOB on Aadhaar
    dob_pos = text.find("DOB")
    if dob_pos > 0:
        block = text[:dob_pos]
        lines = [x.strip() for x in block.split("\n") if x.strip()]
        if len(lines) >= 1:
            return lines[-1]   # last line before DOB
    return None


def extract_dob(text):
    dob = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    return dob.group(1) if dob else None


def extract_address(text):
    m = re.search(r"(C/O.*?\d{6})", text, re.DOTALL)
    if m:
        addr = m.group(1)
        addr = addr.replace("\n", " ")
        return addr.strip()
    return None


def extract_pan(text):
    m = re.search(r"[A-Z]{5}\d{4}[A-Z]", text)
    return m.group(0) if m else None


def run_ocr_agent(app_id: int, file_path: str):
    text = extract_text_from_file(file_path)

    name = extract_name(text)
    dob = extract_dob(text)
    address = extract_address(text)
    pan = extract_pan(text)

    db = SessionLocal()
    kyc = KYCData(
        app_id=app_id,
        extracted_name=name,
        extracted_dob=dob,
        extracted_pan=pan,
        extracted_address=address,
        ocr_confidence=0.85,
        updated_at=datetime.now(),
    )
    db.add(kyc)
    db.commit()
    db.close()

    return {
        "extracted_name": name,
        "extracted_dob": dob,
        "extracted_pan": pan,
        "extracted_address": address
    }
