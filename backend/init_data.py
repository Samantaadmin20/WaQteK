import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

from server import (
    User, Employee, LeaveBalance, SickDays, AuditLog,
    UserRole, Department, hash_password
)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def initialize_database():
    """Initialize the database with sample data"""
    
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🚀 Initializing WaQteK HR Database...")
    
    # Clear existing data
    await db.users.delete_many({})
    await db.employees.delete_many({})
    await db.leave_balances.delete_many({})
    await db.sick_days.delete_many({})
    await db.audit_logs.delete_many({})
    
    print("✅ Cleared existing data")
    
    # Sample users data
    sample_users = [
        # Admin account
        {
            "email": "admin@waqtek.com",
            "password": "admin123",
            "role": UserRole.ADMIN,
            "full_name": "System Administrator",
            "department": Department.IT,
            "position": "System Admin",
            "phone": "+1234567890"
        },
        # HR accounts
        {
            "email": "hr1@waqtek.com",
            "password": "hr123",
            "role": UserRole.HR,
            "full_name": "Sara Ahmed",
            "department": Department.HR,
            "position": "HR Manager",
            "phone": "+1234567891"
        },
        {
            "email": "hr2@waqtek.com",
            "password": "hr123",
            "role": UserRole.HR,
            "full_name": "Omar Hassan",
            "department": Department.HR,
            "position": "HR Specialist",
            "phone": "+1234567892"
        },
        # Manager accounts
        {
            "email": "manager1@waqtek.com",
            "password": "manager123",
            "role": UserRole.MANAGER,
            "full_name": "Ahmed Ali",
            "department": Department.IT,
            "position": "IT Manager",
            "phone": "+1234567893"
        },
        {
            "email": "manager2@waqtek.com",
            "password": "manager123",
            "role": UserRole.MANAGER,
            "full_name": "Fatima Al-Zahra",
            "department": Department.MARKETING,
            "position": "Marketing Manager",
            "phone": "+1234567894"
        },
        {
            "email": "manager3@waqtek.com",
            "password": "manager123",
            "role": UserRole.MANAGER,
            "full_name": "Khalid Rashid",
            "department": Department.SALES,
            "position": "Sales Manager",
            "phone": "+1234567895"
        },
        # Employee accounts
        {
            "email": "emp1@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Amina Mahmoud",
            "department": Department.IT,
            "position": "Software Developer",
            "phone": "+1234567896"
        },
        {
            "email": "emp2@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Youssef Ibrahim",
            "department": Department.IT,
            "position": "Frontend Developer",
            "phone": "+1234567897"
        },
        {
            "email": "emp3@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Layla Saad",
            "department": Department.MARKETING,
            "position": "Marketing Specialist",
            "phone": "+1234567898"
        },
        {
            "email": "emp4@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Hassan Farid",
            "department": Department.SALES,
            "position": "Sales Executive",
            "phone": "+1234567899"
        },
        {
            "email": "emp5@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Nour Abdel-Rahman",
            "department": Department.FINANCE,
            "position": "Accountant",
            "phone": "+1234567800"
        },
        {
            "email": "emp6@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Tariq Mohsen",
            "department": Department.OPERATIONS,
            "position": "Operations Coordinator",
            "phone": "+1234567801"
        },
        {
            "email": "emp7@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Rana Khaled",
            "department": Department.HR,
            "position": "HR Assistant",
            "phone": "+1234567802"
        },
        {
            "email": "emp8@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Mahmoud Nasser",
            "department": Department.IT,
            "position": "DevOps Engineer",
            "phone": "+1234567803"
        },
        {
            "email": "emp9@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Dina Farouk",
            "department": Department.MARKETING,
            "position": "Content Creator",
            "phone": "+1234567804"
        },
        {
            "email": "emp10@waqtek.com",
            "password": "emp123",
            "role": UserRole.EMPLOYEE,
            "full_name": "Karim Mostafa",
            "department": Department.SALES,
            "position": "Sales Representative",
            "phone": "+1234567805"
        }
    ]
    
    created_users = []
    created_employees = []
    
    # Create users and employees
    for user_data in sample_users:
        # Create user account
        user = User(
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            role=user_data["role"],
            created_at=datetime.utcnow() - timedelta(days=30)  # Created 30 days ago
        )
        
        await db.users.insert_one(user.dict())
        created_users.append(user)
        
        # Create employee record
        employee = Employee(
            user_id=user.id,
            full_name=user_data["full_name"],
            email=user_data["email"],
            department=user_data["department"],
            position=user_data["position"],
            hire_date=datetime.utcnow() - timedelta(days=90),  # Hired 90 days ago
            phone_number=user_data["phone"],
            initial_leave_balance=20.0,  # 20 days initial leave
            created_by="system",
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        
        await db.employees.insert_one(employee.dict())
        created_employees.append(employee)
        
        # Create leave balance records
        current_date = datetime.utcnow()
        leave_balance = LeaveBalance(
            employee_id=employee.id,
            year=current_date.year,
            month=current_date.month,
            opening_balance=20.0,
            leave_taken=0.0,
            hr_adjustments=0.0,
            closing_balance=20.0,
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        
        await db.leave_balances.insert_one(leave_balance.dict())
        
        # Create sick days record
        sick_days = SickDays(
            employee_id=employee.id,
            year=current_date.year,
            used_days=0,
            total_allowed=3,
            last_reset=datetime.utcnow() - timedelta(days=30)
        )
        
        await db.sick_days.insert_one(sick_days.dict())
    
    # Create some sample audit logs
    audit_logs = [
        AuditLog(
            user_id=created_users[0].id,  # Admin
            action="SYSTEM_INITIALIZATION",
            target_type="system",
            target_id="database",
            details={"message": "Database initialized with sample data"},
            timestamp=datetime.utcnow()
        )
    ]
    
    for log in audit_logs:
        await db.audit_logs.insert_one(log.dict())
    
    print("✅ Sample data created successfully!")
    print(f"📊 Created {len(created_users)} users and {len(created_employees)} employees")
    print("\n🔐 Sample Login Credentials:")
    print("Admin: admin@waqtek.com / admin123")
    print("HR: hr1@waqtek.com / hr123")
    print("Manager: manager1@waqtek.com / manager123")
    print("Employee: emp1@waqtek.com / emp123")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(initialize_database())