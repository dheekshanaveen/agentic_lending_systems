# backend/routers/ocr.py
import os
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from backend.agents.aadhar_agent import run_aadhaar_ocr_agent
from backend.agents.pan_agent import run_pan_ocr_agent

router = APIRouter(prefix="/agent/ocr", tags=["OCR Agents"])


def _save_temp_upload(upload: UploadFile) -> str:
    """Save UploadFile to a temporary file and return its path."""
    suffix = os.path.splitext(upload.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        with tmp as f:
            shutil.copyfileobj(upload.file, f)
        return tmp.name
    except Exception:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise


@router.post("/both")
async def ocr_both(
    app_id: int = Form(...),
    aadhaar_document: Optional[UploadFile] = File(None),
    pan_document: Optional[UploadFile] = File(None),
):
    """
    Run Aadhaar agent and PAN agent (if corresponding file provided).
    Form fields:
      - app_id (int)
      - aadhaar_document (file) optional
      - pan_document (file) optional

    Returns combined JSON with keys 'aadhaar' and 'pan' (only present if ran).
    """

    results = {}
    temp_paths = []

    try:
        # Aadhaar
        if aadhaar_document:
            aadhaar_path = _save_temp_upload(aadhaar_document)
            temp_paths.append(aadhaar_path)
            aadhaar_res = run_aadhaar_ocr_agent(app_id, aadhaar_path)
            results["aadhaar"] = aadhaar_res

        # PAN
        if pan_document:
            pan_path = _save_temp_upload(pan_document)
            temp_paths.append(pan_path)
            pan_res = run_pan_ocr_agent(app_id, pan_path)
            results["pan"] = pan_res

        if not (aadhaar_document or pan_document):
            return {"error": "No documents provided. Provide at least aadhaar_document or pan_document."}

        # Decide combined KYC status optionally (simple aggregator)
        # If both present, both must be APPROVED -> overall APPROVED, else REJECTED.
        # If only one agent present, use that agent's status.
        overall = {}
        statuses = []
        if "aadhaar" in results and isinstance(results["aadhaar"], dict) and "kyc_status" in results["aadhaar"]:
            statuses.append(results["aadhaar"]["kyc_status"])
        if "pan" in results and isinstance(results["pan"], dict) and "kyc_status" in results["pan"]:
            statuses.append(results["pan"]["kyc_status"])

        if statuses:
            if all(s == "APPROVED" for s in statuses):
                overall_status = "APPROVED"
            else:
                overall_status = "REJECTED"
            overall["combined_kyc_status"] = overall_status
            overall["individual_statuses"] = statuses
        else:
            overall["combined_kyc_status"] = "UNKNOWN"

        return {"results": results, "overall": overall}

    finally:
        # cleanup temp files
        for p in temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass
