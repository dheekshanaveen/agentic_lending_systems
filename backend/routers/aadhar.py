from fastapi import APIRouter, UploadFile, File, Form
from backend.agents.aadhar_agent import process_aadhar_ocr

router = APIRouter(prefix="/agent/aadhar", tags=["Aadhar OCR"])

@router.post("/")
def aadhar_ocr(app_id: int = Form(...), document: UploadFile = File(...)):
    return process_aadhar_ocr(app_id, document)
