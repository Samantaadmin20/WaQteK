from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import bcrypt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="WaQteK HR Management System", version="1.0.0")

# Create API router
api_router = APIRouter(prefix="/api")

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class Department(str, Enum):
    IT = "IT"
    HR = "HR"
    FINANCE = "Finance"
    MARKETING = "Marketing"
    OPERATIONS = "Operations"
    SALES = "Sales"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Employee(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    full_name: str
    email: EmailStr
    department: Department
    position: str
    hire_date: datetime
    phone_number: str
    initial_leave_balance: float = 0.0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

class EmployeeCreate(BaseModel):
    full_name: str
    email: EmailStr
    department: Department
    position: str
    hire_date: datetime
    phone_number: str
    initial_leave_balance: float = 0.0
    password: str
    role: UserRole

class LeaveBalance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    year: int
    month: int
    opening_balance: float
    leave_taken: float = 0.0
    hr_adjustments: float = 0.0
    closing_balance: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LeaveAdjustment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    adjustment_amount: float  # +1, -1, +0.5, -0.5
    reason: str
    adjusted_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SickDays(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    year: int
    used_days: int = 0
    total_allowed: int = 3
    last_reset: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    action: str
    target_type: str
    target_id: str
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Response models
class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: UserRole

class EmployeeResponse(BaseModel):
    id: str
    full_name: str
    email: str
    department: str
    position: str
    hire_date: datetime
    phone_number: str
    current_leave_balance: float
    sick_days_used: int
    sick_days_remaining: int

# Utility functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def require_role(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker

async def log_audit(user_id: str, action: str, target_type: str, target_id: str, details: Dict[str, Any]):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    await db.audit_logs.insert_one(audit_log.dict())

# Authentication endpoints
@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    access_token = create_access_token(data={"sub": user["id"]})
    await log_audit(user["id"], "LOGIN", "user", user["id"], {"email": user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_role": user["role"]
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }

# Employee management endpoints
@api_router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR]))
):
    # Check if user with email already exists
    existing_user = await db.users.find_one({"email": employee_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # HR can only create Employee and Manager roles
    if current_user.role == UserRole.HR and employee_data.role not in [UserRole.EMPLOYEE, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="HR can only create Employee and Manager roles")
    
    # Create user account
    user = User(
        email=employee_data.email,
        password_hash=hash_password(employee_data.password),
        role=employee_data.role
    )
    await db.users.insert_one(user.dict())
    
    # Create employee record
    employee = Employee(
        user_id=user.id,
        full_name=employee_data.full_name,
        email=employee_data.email,
        department=employee_data.department,
        position=employee_data.position,
        hire_date=employee_data.hire_date,
        phone_number=employee_data.phone_number,
        initial_leave_balance=employee_data.initial_leave_balance,
        created_by=current_user.id
    )
    await db.employees.insert_one(employee.dict())
    
    # Initialize leave balance
    current_date = datetime.utcnow()
    leave_balance = LeaveBalance(
        employee_id=employee.id,
        year=current_date.year,
        month=current_date.month,
        opening_balance=employee_data.initial_leave_balance,
        closing_balance=employee_data.initial_leave_balance
    )
    await db.leave_balances.insert_one(leave_balance.dict())
    
    # Initialize sick days
    sick_days = SickDays(
        employee_id=employee.id,
        year=current_date.year
    )
    await db.sick_days.insert_one(sick_days.dict())
    
    await log_audit(
        current_user.id,
        "CREATE_EMPLOYEE",
        "employee",
        employee.id,
        {"employee_name": employee.full_name, "email": employee.email}
    )
    
    return EmployeeResponse(
        id=employee.id,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department.value,
        position=employee.position,
        hire_date=employee.hire_date,
        phone_number=employee.phone_number,
        current_leave_balance=employee_data.initial_leave_balance,
        sick_days_used=0,
        sick_days_remaining=3
    )

@api_router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR, UserRole.MANAGER]))
):
    employees = await db.employees.find({"is_active": True}).to_list(1000)
    response = []
    
    for emp in employees:
        # Get current leave balance
        current_date = datetime.utcnow()
        leave_balance = await db.leave_balances.find_one({
            "employee_id": emp["id"],
            "year": current_date.year,
            "month": current_date.month
        })
        
        current_balance = leave_balance["closing_balance"] if leave_balance else 0.0
        
        # Get sick days
        sick_days = await db.sick_days.find_one({
            "employee_id": emp["id"],
            "year": current_date.year
        })
        
        sick_days_used = sick_days["used_days"] if sick_days else 0
        
        response.append(EmployeeResponse(
            id=emp["id"],
            full_name=emp["full_name"],
            email=emp["email"],
            department=emp["department"],
            position=emp["position"],
            hire_date=emp["hire_date"],
            phone_number=emp["phone_number"],
            current_leave_balance=current_balance,
            sick_days_used=sick_days_used,
            sick_days_remaining=3 - sick_days_used
        ))
    
    return response

@api_router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR, UserRole.MANAGER]))
):
    employee = await db.employees.find_one({"id": employee_id, "is_active": True})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get current leave balance
    current_date = datetime.utcnow()
    leave_balance = await db.leave_balances.find_one({
        "employee_id": employee_id,
        "year": current_date.year,
        "month": current_date.month
    })
    
    current_balance = leave_balance["closing_balance"] if leave_balance else 0.0
    
    # Get sick days
    sick_days = await db.sick_days.find_one({
        "employee_id": employee_id,
        "year": current_date.year
    })
    
    sick_days_used = sick_days["used_days"] if sick_days else 0
    
    return EmployeeResponse(
        id=employee["id"],
        full_name=employee["full_name"],
        email=employee["email"],
        department=employee["department"],
        position=employee["position"],
        hire_date=employee["hire_date"],
        phone_number=employee["phone_number"],
        current_leave_balance=current_balance,
        sick_days_used=sick_days_used,
        sick_days_remaining=3 - sick_days_used
    )

# Leave management endpoints
@api_router.post("/leave/adjust/{employee_id}")
async def adjust_leave_balance(
    employee_id: str,
    adjustment: float,
    reason: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR]))
):
    # Validate adjustment amount
    if adjustment not in [1.0, -1.0, 0.5, -0.5]:
        raise HTTPException(status_code=400, detail="Invalid adjustment amount")
    
    # Check if employee exists
    employee = await db.employees.find_one({"id": employee_id, "is_active": True})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get or create current month's leave balance
    current_date = datetime.utcnow()
    leave_balance = await db.leave_balances.find_one({
        "employee_id": employee_id,
        "year": current_date.year,
        "month": current_date.month
    })
    
    if not leave_balance:
        # Create new balance record
        leave_balance = LeaveBalance(
            employee_id=employee_id,
            year=current_date.year,
            month=current_date.month,
            opening_balance=0.0,
            closing_balance=0.0
        )
        await db.leave_balances.insert_one(leave_balance.dict())
    
    # Calculate new balance
    new_balance = leave_balance["closing_balance"] + adjustment
    
    # Update leave balance
    await db.leave_balances.update_one(
        {"id": leave_balance["id"]},
        {
            "$set": {"closing_balance": new_balance},
            "$inc": {"hr_adjustments": adjustment}
        }
    )
    
    # Record adjustment
    adjustment_record = LeaveAdjustment(
        employee_id=employee_id,
        adjustment_amount=adjustment,
        reason=reason,
        adjusted_by=current_user.id
    )
    await db.leave_adjustments.insert_one(adjustment_record.dict())
    
    await log_audit(
        current_user.id,
        "ADJUST_LEAVE_BALANCE",
        "employee",
        employee_id,
        {
            "employee_name": employee["full_name"],
            "adjustment": adjustment,
            "reason": reason,
            "new_balance": new_balance
        }
    )
    
    return {
        "message": "Leave balance adjusted successfully",
        "new_balance": new_balance,
        "adjustment": adjustment
    }

class LeaveAdjustmentRequest(BaseModel):
    adjustment: float
    reason: str

@api_router.post("/leave/adjust/{employee_id}/body")
async def adjust_leave_balance_body(
    employee_id: str,
    request: LeaveAdjustmentRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR]))
):
    return await adjust_leave_balance(employee_id, request.adjustment, request.reason, current_user)

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "WaQteK HR Management System"}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)