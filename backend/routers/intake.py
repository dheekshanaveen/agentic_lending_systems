# backend/routers/intake.py
from fastapi import APIRouter, HTTPException
from backend.schemas.request_schemas import ApplicationRequest
from backend.database import SessionLocal
from backend.models.db_models import Application

router = APIRouter(prefix="/apply", tags=["Application"])


@router.post("/", status_code=201)
def apply(req: ApplicationRequest):
    db = SessionLocal()
    try:
        # req.dob is already datetime.date (validator handled parsing)
        app = Application(
            name=req.name,
            dob=req.dob,
            phone=req.phone,
            email=req.email,
            aadhaar=req.aadhaar_number,
            pan=req.pan,
            address=req.address,
            income=req.income,
            loan_amount=req.loan_amount,
            loan_tenure=req.loan_tenure,
        )

        db.add(app)
        db.commit()
        db.refresh(app)

        return {"application_id": app.app_id, "status": "Application Received"}

    except Exception as e:
        db.rollback()
        # Return a clear HTTP error rather than an internal silent failure
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        db.close()
