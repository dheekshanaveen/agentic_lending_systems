from fastapi import APIRouter
from backend.schemas.request_schemas import ApplicationRequest
from backend.database import SessionLocal
from backend.models.db_models import Application
from datetime import datetime

router = APIRouter(prefix="/apply", tags=["Application"])


@router.post("/")
def apply(req: ApplicationRequest):
    db = SessionLocal()

    dob = datetime.strptime(req.dob, "%Y-%m-%d").date()

    app = Application(
        name=req.name,
        dob=dob,
        phone=req.phone,
        email=req.email,
        aadhaar_number=req.aadhaar_number,   # FIXED
        pan=req.pan,
        address=req.address,
        income=req.income,
        loan_amount=req.loan_amount,
        loan_tenure=req.loan_tenure
    )

    db.add(app)
    db.commit()
    db.refresh(app)
    db.close()

    return {"application_id": app.app_id, "status": "Application Received"}
