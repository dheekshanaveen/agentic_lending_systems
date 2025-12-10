from fastapi import APIRouter
from backend.schemas.request_schemas import ApplicationRequest
from backend.agents.intake_agent import create_application

router = APIRouter(prefix="/apply", tags=["Application"])

@router.post("/")
def apply(req: ApplicationRequest):
    app_id = create_application(req)
    return {"application_id": app_id, "status": "Application Received"}
