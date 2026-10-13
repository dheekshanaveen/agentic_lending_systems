# backend/agents/salary_agent.py
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from backend.database import SessionLocal
from backend.models.db_models import Application  # use or import your models
# from backend.models.db_models import SalarySlip  # if you added ORM models

# reuse tesseract path if needed
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_file(file_path: str) -> str:
    """
    Full-document OCR using pdf2image + tesseract.
    Returns the concatenated text.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=300)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p, lang="eng", config="--psm 3")
        return text
    else:
        return pytesseract.image_to_string(file_path, lang="eng", config="--psm 3")

# ---- Gemini call placeholder ----
def call_gemini_extract(extracted_text: str, doc_type: str = "salary") -> Dict[str,Any]:
    """
    Send extracted_text to Gemini/LLM to extract structured fields.
    Replace with your actual Gemini client call.
    Must return a dict with expected keys (see prompt below).
    Example return for salary:
    {
      "employee_name": "Dheeksha N",
      "employee_id": "EMP12345",
      "employer": "Acme Pvt Ltd",
      "month": "2025-10",
      "gross_amount": 45000,
      "net_amount": 38000,
      "salary_lines": [ ... ]   # optional detailed lines
    }
    """
    # ---- INSERT YOUR GEMINI API CALL HERE ----
    # Example (pseudocode):
    # from google.ai import ... or openai client depending on provider
    # response = client.generate(model="gemini-2.5-flash", prompt=..., temperature=0)
    # parsed = json.loads(response.text)
    # return parsed

    # Temporary stub for local dev (VERY IMPORTANT: replace)
    return {
        "employee_name": None,
        "employee_id": None,
        "employer": None,
        "month": None,
        "gross_amount": None,
        "net_amount": None,
        "salary_lines": []
    }

# ---- Post-processing / validation ----
def normalize_currency_value(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    # remove commas, rupee symbol, etc.
    s = str(s)
    s = s.replace("₹", "").replace(",", "").strip()
    m = re.search(r"[-+]?\d+(\.\d+)?", s)
    if m:
        return float(m.group(0))
    try:
        return float(s)
    except Exception:
        return None

def run_salary_agent(app_id: int, file_path: str) -> Dict[str,Any]:
    db = SessionLocal()
    try:
        intake = db.query(Application).filter(Application.app_id == app_id).first()
        if not intake:
            return {"error":"Invalid application id"}

        text = extract_text_from_file(file_path)

        # Call Gemini LLM to extract structured fields
        parsed = call_gemini_extract(text, doc_type="salary")

        # normalize numeric fields
        parsed["gross_amount"] = normalize_currency_value(parsed.get("gross_amount"))
        parsed["net_amount"]   = normalize_currency_value(parsed.get("net_amount"))

        # basic cross-check: name match
        name_match = False
        try:
            if parsed.get("employee_name") and intake.name:
                from fuzzywuzzy import fuzz
                name_match = fuzz.ratio((intake.name or "").lower(), parsed.get("employee_name").lower()) >= 70
        except Exception:
            name_match = False

        # save into DB (example simple insert into salary_slips table using raw SQL or ORM)
        # For simplicity: write into kyc_data or a dedicated table as you prefer
        # Example: insert into salary_slips table using sqlite (or via SQLAlchemy model)
        # Keep parsed JSON for auditing
        record = {
            "app_id": app_id,
            "file_path": file_path,
            "employer": parsed.get("employer"),
            "employee_name": parsed.get("employee_name"),
            "employee_id": parsed.get("employee_id"),
            "month": parsed.get("month"),
            "gross_amount": parsed.get("gross_amount"),
            "net_amount": parsed.get("net_amount"),
            "parsed_json": json.dumps(parsed),
            "ocr_confidence": None,
            "created_at": datetime.now().isoformat()
        }
        # TODO: Persist via SQLAlchemy model or raw SQL

        # Return structured result
        return {
            "parsed": parsed,
            "name_match": name_match,
            "status": "EXTRACTED"
        }

    except Exception as e:
        return {"error":"Internal error in salary agent", "details": str(e)}
    finally:
        db.close()
