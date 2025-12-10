from pydantic import BaseModel

class ApplicationRequest(BaseModel):
    name: str
    dob: str
    phone: str
    email: str
    pan: str
    address: str
    income: int
    loan_amount: int
    loan_tenure: int
