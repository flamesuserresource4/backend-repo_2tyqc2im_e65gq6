import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import User

app = FastAPI(title="FlamesBlue HRIS+ERP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------
# Utilities & Auth
# ----------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    email: EmailStr
    name: str
    role: str
    token: str


def issue_token(email: str, role: str) -> str:
    # Simple demo token in format role:email (base64-like without security)
    # Replace with JWT for production use
    raw = f"{role}:{email}"
    return raw.encode().hex()


def parse_token(token: str) -> Dict[str, str]:
    try:
        decoded = bytes.fromhex(token).decode()
        role, email = decoded.split(":", 1)
        return {"role": role, "email": email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    token = parts[-1]
    payload = parse_token(token)
    user = db["user"].find_one({"email": payload["email"]})
    if not user or user.get("is_active") is not True:
        raise HTTPException(status_code=401, detail="User not active or not found")
    return {"email": payload["email"], "role": payload["role"], "name": user.get("name", payload["email"]) }


# ----------------------
# Startup: seed default users
# ----------------------
@app.on_event("startup")
def seed_users():
    if db is None:
        return
    # Ensure email index
    try:
        db["user"].create_index("email", unique=True)
    except Exception:
        pass

    # Seed admin
    if db["user"].count_documents({"email": "admin"}) == 0:
        create_document("user", User(email="admin", password="admin", name="Administrator", role="admin", is_active=True))
    # Seed employee
    if db["user"].count_documents({"email": "karyawan"}) == 0:
        create_document("user", User(email="karyawan", password="karyawan", name="Karyawan", role="employee", is_active=True))


# ----------------------
# Basic routes
# ----------------------
@app.get("/")
def root():
    return {"message": "FlamesBlue HRIS+ERP Backend", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# ----------------------
# Auth endpoints
# ----------------------
@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    user = db["user"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User is inactive")
    token = issue_token(payload.email, user.get("role", "employee"))
    return LoginResponse(email=payload.email, name=user.get("name", payload.email), role=user.get("role", "employee"), token=token)


@app.get("/auth/me")
def me(current = Depends(get_current_user)):
    return current


# ----------------------
# Admin-only sample endpoint
# ----------------------
@app.get("/admin/users")
def list_users(current = Depends(get_current_user)):
    if current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    items = get_documents("user", {}, limit=100)
    # redact passwords
    for it in items:
        it.pop("password", None)
        it["_id"] = str(it.get("_id"))
    return {"count": len(items), "items": items}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
