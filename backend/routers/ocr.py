from fastapi import APIRouter, UploadFile, File, Form
from backend.agents.ocr_aadhaar_agent import run_aadhaar_ocr_agent
import shutil
import uuid

router = APIRouter(prefix="/agent/ocr", tags=["OCR"])


@router.post("/aadhaar")
def aadhaar_ocr(app_id: int = Form(...), document: UploadFile = File(...)):
    file_name = f"temp_{uuid.uuid4()}.jpg"

    with open(file_name, "wb") as buffer:
        shutil.copyfileobj(document.file, buffer)

    result = run_aadhaar_ocr_agent(app_id, file_name)
    return result
