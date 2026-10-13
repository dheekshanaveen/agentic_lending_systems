# backend/routers/income.py
import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.agents.income_agent import run_income_agent

router = APIRouter(prefix="/agent/income", tags=["Income Verification"])


def _save_temp_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename)[1] or ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    with tmp as f:
        shutil.copyfileobj(upload.file, f)
    return tmp.name


@router.post("/upload_and_verify")
async def upload_and_verify(
    app_id: int = Form(...),
    salary_files: List[UploadFile] = File(...),   # expect 1..3 files
    bank_files: Optional[List[UploadFile]] = File(None)  # expect up to 6
):
    if not salary_files or len(salary_files) < 1:
        raise HTTPException(status_code=400, detail="At least 1 salary slip required (recommend 3).")
    if bank_files is None:
        bank_files = []

    salary_paths = []
    bank_paths = []
    try:
        for f in salary_files:
            p = _save_temp_upload(f)
            salary_paths.append(p)
        for f in bank_files:
            p = _save_temp_upload(f)
            bank_paths.append(p)

        # by default use_gemini=False; change to True once integrated
        res = run_income_agent(app_id, salary_paths, bank_paths, use_gemini=False)
        return res
    finally:
        # cleanup uploaded files
        for p in salary_paths + bank_paths:
            try:
                os.remove(p)
            except Exception:
                pass
