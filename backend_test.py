import requests
import unittest
import json
from datetime import datetime

class WaQteKHRSystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = "https://ed1618e0-3d7a-4bce-83c6-5e559a2200ad.preview.emergentagent.com/api"
        cls.admin_credentials = {"email": "admin@waqtek.com", "password": "admin123"}
        cls.hr_credentials = {"email": "hr1@waqtek.com", "password": "hr123"}
        cls.manager_credentials = {"email": "manager1@waqtek.com", "password": "manager123"}
        cls.employee_credentials = {"email": "emp1@waqtek.com", "password": "emp123"}
        cls.tokens = {}
        
        # Login with all roles and store tokens
        print("Logging in with all roles...")
        
        # Admin login
        response = requests.post(f"{cls.base_url}/auth/login", json=cls.admin_credentials)
        if response.status_code == 200:
            data = response.json()
            cls.tokens["admin"] = data["access_token"]
            print("✅ Admin login successful")
        else:
            print(f"❌ Admin login failed: {response.text}")
        
        # HR login
        response = requests.post(f"{cls.base_url}/auth/login", json=cls.hr_credentials)
        if response.status_code == 200:
            data = response.json()
            cls.tokens["hr"] = data["access_token"]
            print("✅ HR login successful")
        else:
            print(f"❌ HR login failed: {response.text}")
        
        # Manager login
        response = requests.post(f"{cls.base_url}/auth/login", json=cls.manager_credentials)
        if response.status_code == 200:
            data = response.json()
            cls.tokens["manager"] = data["access_token"]
            print("✅ Manager login successful")
        else:
            print(f"❌ Manager login failed: {response.text}")
        
        # Employee login
        response = requests.post(f"{cls.base_url}/auth/login", json=cls.employee_credentials)
        if response.status_code == 200:
            data = response.json()
            cls.tokens["employee"] = data["access_token"]
            print("✅ Employee login successful")
        else:
            print(f"❌ Employee login failed: {response.text}")
    
    def test_01_health_check(self):
        """Test the health check endpoint"""
        response = requests.get(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "WaQteK HR Management System")
        print("✅ Health check endpoint is working")
    
    def test_02_get_current_user(self):
        """Test getting current user info"""
        for role, token in self.tokens.items():
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.base_url}/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["role"], role)
            print(f"✅ Get current user info for {role} successful")
    
    def test_03_get_employees_access_control(self):
        """Test role-based access control for getting employees"""
        # Admin, HR, and Manager should be able to get employees
        for role in ["admin", "hr", "manager"]:
            headers = {"Authorization": f"Bearer {self.tokens[role]}"}
            response = requests.get(f"{self.base_url}/employees", headers=headers)
            self.assertEqual(response.status_code, 200)
            employees = response.json()
            self.assertIsInstance(employees, list)
            print(f"✅ {role.capitalize()} can access employees list")
        
        # Employee should not be able to get all employees
        headers = {"Authorization": f"Bearer {self.tokens['employee']}"}
        response = requests.get(f"{self.base_url}/employees", headers=headers)
        self.assertEqual(response.status_code, 403)
        print("✅ Employee cannot access employees list (correctly forbidden)")
    
    def test_04_leave_adjustment_access_control(self):
        """Test role-based access control for leave adjustments"""
        # Get an employee ID first
        headers = {"Authorization": f"Bearer {self.tokens['hr']}"}
        response = requests.get(f"{self.base_url}/employees", headers=headers)
        employees = response.json()
        employee_id = employees[0]["id"]
        
        # Admin and HR should be able to adjust leave
        for role in ["admin", "hr"]:
            headers = {"Authorization": f"Bearer {self.tokens[role]}"}
            adjustment_data = {"adjustment": 1, "reason": f"Test adjustment by {role}"}
            response = requests.post(
                f"{self.base_url}/leave/adjust/{employee_id}/body", 
                json=adjustment_data,
                headers=headers
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["adjustment"], 1)
            print(f"✅ {role.capitalize()} can adjust leave balance")
        
        # Manager and Employee should not be able to adjust leave
        for role in ["manager", "employee"]:
            headers = {"Authorization": f"Bearer {self.tokens[role]}"}
            adjustment_data = {"adjustment": 1, "reason": f"Test adjustment by {role}"}
            response = requests.post(
                f"{self.base_url}/leave/adjust/{employee_id}/body", 
                json=adjustment_data,
                headers=headers
            )
            self.assertEqual(response.status_code, 403)
            print(f"✅ {role.capitalize()} cannot adjust leave balance (correctly forbidden)")
    
    def test_05_leave_adjustment_validation(self):
        """Test validation for leave adjustments"""
        # Get an employee ID first
        headers = {"Authorization": f"Bearer {self.tokens['hr']}"}
        response = requests.get(f"{self.base_url}/employees", headers=headers)
        employees = response.json()
        employee_id = employees[0]["id"]
        
        # Test valid adjustment amounts
        valid_adjustments = [1.0, 0.5, -0.5, -1.0]
        for adjustment in valid_adjustments:
            adjustment_data = {"adjustment": adjustment, "reason": f"Test adjustment of {adjustment}"}
            response = requests.post(
                f"{self.base_url}/leave/adjust/{employee_id}/body", 
                json=adjustment_data,
                headers=headers
            )
            self.assertEqual(response.status_code, 200)
            print(f"✅ Valid adjustment of {adjustment} accepted")
        
        # Test invalid adjustment amount
        invalid_adjustment = {"adjustment": 2, "reason": "Invalid adjustment"}
        response = requests.post(
            f"{self.base_url}/leave/adjust/{employee_id}/body", 
            json=invalid_adjustment,
            headers=headers
        )
        self.assertEqual(response.status_code, 400)
        print("✅ Invalid adjustment amount correctly rejected")
    
    def test_06_employee_details(self):
        """Test getting employee details"""
        # Get an employee ID first
        headers = {"Authorization": f"Bearer {self.tokens['hr']}"}
        response = requests.get(f"{self.base_url}/employees", headers=headers)
        employees = response.json()
        employee_id = employees[0]["id"]
        
        # Get employee details
        response = requests.get(f"{self.base_url}/employees/{employee_id}", headers=headers)
        self.assertEqual(response.status_code, 200)
        employee = response.json()
        
        # Verify employee data structure
        required_fields = [
            "id", "full_name", "email", "department", "position", 
            "hire_date", "phone_number", "current_leave_balance",
            "sick_days_used", "sick_days_remaining"
        ]
        for field in required_fields:
            self.assertIn(field, employee)
        
        # Verify sick days calculation
        self.assertEqual(employee["sick_days_remaining"], 3 - employee["sick_days_used"])
        print("✅ Employee details retrieved successfully with correct structure")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)