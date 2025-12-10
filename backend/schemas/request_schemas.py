from pydantic import BaseModel
from datetime import date

class ApplicationRequest(BaseModel):
    name: str
    dob: date
    phone: str
    email: str
    aadhaar_number: str
    pan: str | None = None
    address: str
    income: int
    loan_amount: int
    loan_tenure: int
