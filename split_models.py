import os

models_dir = r"c:\app_at_present\app\models"
os.makedirs(models_dir, exist_ok=True)

with open(r"c:\app_at_present\app\models.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def get_block(name, block_type="class"):
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith(f"{block_type} {name}(") or line.startswith(f"{block_type} {name}:"):
            start_idx = i
            break
            
    if start_idx == -1:
        print(f"Warning: {block_type} {name} not found")
        return ""
        
    comment_start = start_idx
    while comment_start > 0 and (lines[comment_start-1].strip().startswith("#") or lines[comment_start-1].strip() == ""):
        comment_start -= 1
        
    end_idx = start_idx + 1
    while end_idx < len(lines):
        line = lines[end_idx]
        if line.startswith("class ") or line.startswith("def ") or line.startswith("# ==="):
            break
        end_idx += 1
        
    while end_idx > start_idx and lines[end_idx-1].strip() == "":
        end_idx -= 1
        
    return "".join(lines[comment_start:end_idx]) + "\n\n"

imports = """import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db

"""

files = {
    "core.py": {
        "classes": ["UserModule", "User", "Module", "AuditLog", "LoginHistory", "Notification", "Holiday"],
        "defs": ["validate_password_complexity"]
    },
    "hr.py": {
        "classes": ["Department", "Designation", "Shift", "LeavePolicy", "AttendanceRule"],
        "defs": []
    },
    "employee.py": {
        "classes": ["Employee", "Leave", "LeaveBalance", "Attendance", "ProfileUpdateRequest", "EmployeeExpense", "CompOff", "ShiftSwapRequest", "Timesheet", "AttendanceRegularization", "EmployeeDocument"],
        "defs": []
    },
    "pm.py": {
        "classes": ["Project", "ProjectMember", "Task", "Milestone"],
        "defs": []
    },
    "recruitment.py": {
        "classes": ["JobPosting", "Candidate", "Interview"],
        "defs": []
    },
    "performance.py": {
        "classes": ["PerformanceReview"],
        "defs": []
    },
    "finance.py": {
        "classes": ["Expense", "Invoice", "SalaryRecord", "PayrollInput"],
        "defs": []
    }
}

for filename, contents in files.items():
    out = imports
    for d in contents["defs"]:
        out += get_block(d, "def")
    for c in contents["classes"]:
        out += get_block(c, "class")
    
    with open(os.path.join(models_dir, filename), "w", encoding="utf-8") as f:
        f.write(out)

# Write __init__.py
init_content = """from .core import User, Module, UserModule, AuditLog, LoginHistory, Notification, Holiday, validate_password_complexity
from .hr import Department, Designation, Shift, LeavePolicy, AttendanceRule
from .employee import Employee, Leave, LeaveBalance, Attendance, AttendanceRegularization, CompOff, ShiftSwapRequest, Timesheet, ProfileUpdateRequest, EmployeeDocument, EmployeeExpense
from .pm import Project, ProjectMember, Task, Milestone
from .recruitment import JobPosting, Candidate, Interview
from .performance import PerformanceReview
from .finance import Expense, Invoice, SalaryRecord, PayrollInput
"""

with open(os.path.join(models_dir, "__init__.py"), "w", encoding="utf-8") as f:
    f.write(init_content)

print("Split completed successfully")
