from fastapi import APIRouter
from backend.agents.kyc_agent import run_kyc_agent

router = APIRouter(prefix="/agent/kyc", tags=["KYC"])

@router.post("/")
def kyc_process(app_id: int):
    return run_kyc_agent(app_id)
