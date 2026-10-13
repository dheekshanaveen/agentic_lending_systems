# backend/agents/income_agent.py
"""
Income agent stub (full working implementation).
This file provides run_income_agent(app_id, salary_files, bank_files, use_gemini=False)
so backend.routers.income can import it.
Replace call_gemini_extract_* placeholders with real Gemini calls when ready.
"""
import os, json, re
from statistics import median
from datetime import datetime
from typing import List, Dict, Any

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from fuzzywuzzy import fuzz

from backend.database import SessionLocal
from backend.models.db_models import Application, SalarySlip, BankStatement, IncomeVerification

# Optional: set tesseract path if on Windows (adjust if needed)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Helpers
def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        pages = convert_from_path(path, dpi=300)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p, lang="eng", config="--psm 3")
        return text
    else:
        return pytesseract.image_to_string(path, lang="eng", config="--psm 3")

def _to_number(s):
    if s is None:
        return None
    s = str(s).replace("₹","").replace(",","").strip()
    m = re.search(r"[-+]?\d+(\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except:
        return None

# Simple heuristics (fallback) - keep until Gemini integrated
def _heuristic_parse_salary(text: str) -> Dict[str,Any]:
    res = {
        "employee_name": None,
        "employee_id": None,
        "employer": None,
        "month": None,
        "gross_amount": None,
        "net_amount": None
    }
    m = re.search(r"(Employee\s*ID|Emp\.? ID|Employee No\.?|Emp No\.?)[:\s\-]*([A-Z0-9\-]+)", text, re.I)
    if m:
        res["employee_id"] = m.group(2).strip()
    m = re.search(r"(Employee\s*Name|Name of Employee|Name)[:\s\-]*([A-Z][A-Za-z\s\.]{2,50})", text, re.I)
    if m:
        res["employee_name"] = m.group(2).strip()
    m = re.search(r"(Gross\s+Salary|Gross Pay|Gross)[^\d\n\r]*([₹\s\,\d\.]+)", text, re.I)
    if m:
        res["gross_amount"] = _to_number(m.group(2))
    m = re.search(r"(Net\s+Pay|Net Salary|Net)[^\d\n\r]*([₹\s\,\d\.]+)", text, re.I)
    if m:
        res["net_amount"] = _to_number(m.group(2))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        res["employer"] = lines[0][:80]
    return res

def _heuristic_parse_bank(text: str) -> Dict[str,Any]:
    res = {
        "account_holder": None,
        "account_number": None,
        "avg_balance_last_6_months": None,
        "total_inflow_last_3_months": None,
        "transactions": []
    }
    m = re.search(r"(A/c|Account)\s*(No|Number)[:\s]*([A-Z0-9\-]+)", text, re.I)
    if m:
        res["account_number"] = m.group(3).strip()
    m = re.search(r"(Account\s+Holder|Account\s+Name|Name)[:\s]*([A-Z][A-Za-z\s\.]{2,80})", text, re.I)
    if m:
        res["account_holder"] = m.group(2).strip()
    nums = re.findall(r"[^\d](\d{1,3}(?:[,]\d{3})*(?:\.\d+)?)", text.replace("₹"," "))
    values = [_to_number(n) for n in nums if _to_number(n) is not None]
    if values:
        res["total_inflow_last_3_months"] = sum(values[-10:]) if values else None
        res["avg_balance_last_6_months"] = (values[-6] if len(values)>=6 else (sum(values)/len(values) if values else None))
    return res

# Placeholder Gemini calls (replace with real SDK calls)
def call_gemini_extract_salary(extracted_text: str) -> Dict[str,Any]:
    return _heuristic_parse_salary(extracted_text)

def call_gemini_extract_bank(extracted_text: str) -> Dict[str,Any]:
    return _heuristic_parse_bank(extracted_text)

# Main function
def run_income_agent(app_id: int, salary_files: List[str], bank_files: List[str], use_gemini: bool = False) -> Dict[str,Any]:
    db = SessionLocal()
    try:
        intake = db.query(Application).filter(Application.app_id == app_id).first()
        if not intake:
            return {"error":"Invalid application id"}

        salary_parsed = []
        for path in salary_files:
            text = extract_text_from_file(path)
            parsed = call_gemini_extract_salary(text) if use_gemini else _heuristic_parse_salary(text)
            parsed["gross_amount"] = _to_number(parsed.get("gross_amount"))
            parsed["net_amount"] = _to_number(parsed.get("net_amount"))
            rec = SalarySlip(
                app_id=app_id,
                file_path=path,
                employer=parsed.get("employer"),
                employee_name=parsed.get("employee_name"),
                employee_id=parsed.get("employee_id"),
                month=parsed.get("month"),
                gross_amount=parsed.get("gross_amount"),
                net_amount=parsed.get("net_amount"),
                parsed_json=json.dumps(parsed),
                created_at=datetime.now()
            )
            db.add(rec)
            db.commit()
            salary_parsed.append(parsed)

        bank_parsed = []
        for path in bank_files:
            text = extract_text_from_file(path)
            parsed = call_gemini_extract_bank(text) if use_gemini else _heuristic_parse_bank(text)
            rec = BankStatement(
                app_id=app_id,
                file_path=path,
                account_holder=parsed.get("account_holder"),
                account_number=parsed.get("account_number"),
                avg_balance=parsed.get("avg_balance_last_6_months"),
                total_inflow=parsed.get("total_inflow_last_3_months"),
                parsed_json=json.dumps(parsed),
                created_at=datetime.now()
            )
            db.add(rec)
            db.commit()
            bank_parsed.append(parsed)

        reasons = []
        result_status = "APPROVED"

        # name extraction
        names = [p.get("employee_name") for p in salary_parsed if p.get("employee_name")]
        if not names:
            names = [p.get("account_holder") for p in bank_parsed if p.get("account_holder")]
        extracted_name = names[0] if names else None
        emp_ids = [p.get("employee_id") for p in salary_parsed if p.get("employee_id")]
        extracted_emp_id = emp_ids[0] if emp_ids else None

        net_vals = [p.get("net_amount") for p in salary_parsed if p.get("net_amount") is not None]
        gross_vals = [p.get("gross_amount") for p in salary_parsed if p.get("gross_amount") is not None]
        preferred_salary = median(net_vals) if net_vals else (median(gross_vals) if gross_vals else None)

        name_ok = True
        if intake.name and extracted_name:
            try:
                name_ok = fuzz.ratio((intake.name or "").lower(), (extracted_name or "").lower()) >= 70
            except:
                name_ok = False
        else:
            name_ok = False
        if not name_ok:
            reasons.append("name_mismatch")
            result_status = "REJECTED"

        if preferred_salary is None:
            reasons.append("salary_not_found")
            result_status = "REJECTED"
        else:
            tolerance_pct = 0.20
            diff = abs((preferred_salary or 0) - (int(intake.income) if intake.income else 0))
            if intake.income and (diff / max(1, intake.income) > tolerance_pct):
                reasons.append("salary_diff_too_high")
                result_status = "REJECTED"
            round_threshold = 1000
            if diff > round_threshold and "salary_diff_too_high" not in reasons:
                reasons.append("salary_roundoff_mismatch")
                result_status = "REJECTED"

        large_tx_found = False
        multiplier = 5
        for b in bank_parsed:
            tx_total = b.get("total_inflow_last_3_months") or 0
            parsed_tx = b.get("transactions") or []
            if preferred_salary and parsed_tx:
                for t in parsed_tx:
                    amt = t.get("amount") or t.get("value") or None
                    if amt and _to_number(amt) is not None and _to_number(amt) > multiplier * preferred_salary:
                        large_tx_found = True
                        break
            if preferred_salary and tx_total and tx_total > (10 * preferred_salary):
                large_tx_found = True
            if large_tx_found:
                reasons.append("large_bank_transactions")
                result_status = "REJECTED"
                break

        verification = IncomeVerification(
            app_id=app_id,
            status=result_status,
            reason=";".join(reasons) if reasons else "all_checks_passed",
            extracted_name=extracted_name,
            extracted_employee_id=extracted_emp_id,
            extracted_salary=preferred_salary,
            saved_payload=json.dumps({"salary_parsed": salary_parsed, "bank_parsed": bank_parsed}),
            created_at=datetime.now()
        )
        db.add(verification)
        db.commit()

        return {
            "status": result_status,
            "reasons": reasons,
            "extracted_name": extracted_name,
            "extracted_employee_id": extracted_emp_id,
            "extracted_salary": preferred_salary,
            "salary_parsed": salary_parsed,
            "bank_parsed": bank_parsed
        }

    except Exception as e:
        db.rollback()
        return {"error": "Internal error in income agent", "details": str(e)}
    finally:
        db.close()
