from pydantic import BaseModel

class ApplicationRequest(BaseModel):
    name: str
    dob: str
    phone: str
    email: str
    aadhaar_number: str   # FIXED
    pan: str = ""         # optional
    address: str
    income: int
    loan_amount: int
    loan_tenure: int
