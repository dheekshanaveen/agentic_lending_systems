from fastapi import APIRouter, UploadFile, File, Form
from backend.agents.aadhar_agent import run_aadhaar_ocr_agent
import uuid
import shutil

router = APIRouter(prefix="/agent/ocr", tags=["OCR"])


@router.post("/aadhaar")
def aadhaar_ocr(app_id: int = Form(...), document: UploadFile = File(...)):
    ext = document.filename.split(".")[-1]
    temp_name = f"aadhaar_{uuid.uuid4()}.{ext}"

    with open(temp_name, "wb") as f:
        shutil.copyfileobj(document.file, f)

    return run_aadhaar_ocr_agent(app_id, temp_name)
