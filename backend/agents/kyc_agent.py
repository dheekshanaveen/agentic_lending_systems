from datetime import datetime
from backend.database import SessionLocal
from backend.models.db_models import KYCData, KYCResult, Application

def normalize(s):
    return s.lower().replace(" ", "").replace(",", "")

def run_kyc_agent(app_id: int):
    db = SessionLocal()

    intake = db.query(Application).filter(Application.app_id == app_id).first()
    ocr = db.query(KYCData).filter(KYCData.app_id == app_id).first()

    if not intake or not ocr:
        db.close()
        return {"status": "ERROR", "message": "Missing data"}

    name_match = normalize(ocr.extracted_name or "") == normalize(intake.name)
    dob_match = normalize(ocr.extracted_dob or "") == normalize(intake.dob.strftime("%d/%m/%Y"))
    aadhaar_match = normalize(ocr.extracted_pan or "") == normalize(intake.pan)
    address_match = normalize(intake.address) in normalize(ocr.extracted_address or "")

    if name_match and dob_match and aadhaar_match and address_match:
        status = "APPROVED"
    else:
        status = "REJECTED"

    result = KYCResult(
        app_id=app_id,
        pan_verified=aadhaar_match,
        face_match_score=0.90,
        kyc_status=status,
        updated_at=datetime.utcnow(),
    )
    db.add(result)
    db.commit()
    db.close()

    return {
        "app_id": app_id,
        "name_match": name_match,
        "dob_match": dob_match,
        "aadhaar_match": aadhaar_match,
        "address_match": address_match,
        "kyc_status": status
    }
