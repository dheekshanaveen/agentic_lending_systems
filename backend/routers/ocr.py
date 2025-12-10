from fastapi import APIRouter, UploadFile, File, Form
from backend.agents.aadhar_agent import run_aadhaar_ocr_agent
import shutil
import uuid

router = APIRouter(prefix="/agent/ocr", tags=["OCR"])

@router.post("/aadhaar")
def aadhaar_ocr(app_id: int = Form(...), document: UploadFile = File(...)):
    ext = document.filename.split(".")[-1]
    file_name = f"temp_aadhaar_{uuid.uuid4()}.{ext}"

    with open(file_name, "wb") as buffer:
        shutil.copyfileobj(document.file, buffer)

    return run_aadhaar_ocr_agent(app_id, file_name)
