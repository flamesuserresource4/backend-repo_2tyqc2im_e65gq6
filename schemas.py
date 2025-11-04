"""
Database Schemas for HRIS + ERP

Each Pydantic model corresponds to a MongoDB collection.
Collection name is the lowercase of the class name.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr
from datetime import date


class User(BaseModel):
    """Users in the system (admin and employees). Collection: "user"""
    email: str = Field(..., min_length=1, description="Unique login identifier (can be username or email)")
    password: str = Field(..., min_length=3, description="Plain password for demo. Replace with hash in production.")
    name: str = Field(..., description="Full name to display")
    role: Literal["admin", "employee"] = Field(..., description="Role determining access")
    is_active: bool = Field(True, description="Whether user can log in")


class Attendance(BaseModel):
    """Clock-in/clock-out records. Collection: "attendance"""
    user_email: EmailStr = Field(..., description="Email of the user")
    date_str: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    check_in: Optional[str] = Field(None, description="ISO time string for check-in")
    check_out: Optional[str] = Field(None, description="ISO time string for check-out")
    notes: Optional[str] = Field(None, description="Optional notes")


class LeaveRequest(BaseModel):
    """Leave requests. Collection: "leaverequest"""
    user_email: EmailStr
    start_date: date
    end_date: date
    type: Literal["annual", "sick", "unpaid", "other"]
    reason: Optional[str] = None
    status: Literal["pending", "approved", "rejected"] = "pending"


class PayrollItem(BaseModel):
    """Monthly payroll slips. Collection: "payrollitem"""
    user_email: EmailStr
    period: str = Field(..., description="YYYY-MM")
    base_salary: float
    allowances: float = 0
    deductions: float = 0
    net_pay: float


class Kpi(BaseModel):
    """Key performance indicator snapshots. Collection: "kpi"""
    user_email: EmailStr
    period: str = Field(..., description="YYYY-QX or YYYY-MM")
    goals: List[str] = []
    score: Optional[float] = Field(None, ge=0, le=100)
