# backend/agents/bank_agent.py
import os, json, re
from datetime import datetime
from typing import Dict,Any

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from backend.database import SessionLocal
from backend.models.db_models import Application

def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=300)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p, lang="eng", config="--psm 3")
        return text
    else:
        return pytesseract.image_to_string(file_path, lang="eng", config="--psm 3")

def call_gemini_extract_bank(extracted_text: str) -> Dict[str,Any]:
    """
    Ask Gemini to return JSON like:
    {
      "account_holder": "Dheeksha N",
      "account_number": "XXXX1234",
      "monthly_balances": {"2025-06": 20000, ...},
      "avg_balance_last_6_months": 18500.5,
      "total_inflow_last_3_months": 60000,
      "top_inflows": [{ "date":"2025-10-01", "amount": 20000, "desc":"salary" }, ... ],
      "transactions": [...]
    }
    """
    # Replace with real API call
    return {}

def run_bank_agent(app_id: int, file_path: str) -> Dict[str,Any]:
    db = SessionLocal()
    try:
        intake = db.query(Application).filter(Application.app_id == app_id).first()
        if not intake:
            return {"error":"Invalid application id"}

        text = extract_text_from_file(file_path)

        parsed = call_gemini_extract_bank(text)
        # basic checks: account_holder fuzzy match vs intake.name
        name_match = False
        try:
            if parsed.get("account_holder") and intake.name:
                from fuzzywuzzy import fuzz
                name_match = fuzz.ratio(intake.name.lower(), parsed.get("account_holder").lower()) >= 70
        except Exception:
            name_match = False

        # Persist parsed JSON to bank_statements table (or KYC)
        # TODO: implement persistence

        return {
            "parsed": parsed,
            "name_match": name_match,
            "status": "EXTRACTED"
        }
    except Exception as e:
        return {"error": "Internal error in bank agent", "details": str(e)}
    finally:
        db.close()
