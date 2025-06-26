from models import db, Role, Employee, BiometricData, AuthenticationLog
from datetime import datetime, timedelta
import random

def init_database(app):
    with app.app_context():
        db.create_all()
        if Role.query.first() is None:
            create_sample_data()

def create_sample_data():
    # Create Roles
    roles = [
        Role(role_name='Admin', description='System Administrator', security_level=5, max_attempts=5, can_enroll_others=True),
        Role(role_name='Security Officer', description='Security Personnel', security_level=4, max_attempts=4, can_enroll_others=True),
        Role(role_name='Manager', description='Department Manager', security_level=3, max_attempts=3, can_enroll_others=False),
        Role(role_name='Employee', description='Regular Employee', security_level=2, max_attempts=3, can_enroll_others=False)
    ]
    
    for role in roles:
        db.session.add(role)
    db.session.commit()
    
    # Create Employees
    employees = [
        Employee(role_id=1, first_name='John', last_name='Smith', email='john.smith@company.com', department='IT'),
        Employee(role_id=2, first_name='Sarah', last_name='Johnson', email='sarah.johnson@company.com', department='Security'),
        Employee(role_id=3, first_name='Mike', last_name='Davis', email='mike.davis@company.com', department='Finance'),
        Employee(role_id=4, first_name='Emma', last_name='Wilson', email='emma.wilson@company.com', department='HR')
    ]
    
    for employee in employees:
        db.session.add(employee)
    db.session.commit()
    
    # Create Biometric Data
    for employee in Employee.query.all():
        biometric = BiometricData(
            employee_id=employee.employee_id,
            face_encoding=f'FACE_ENCODING_{employee.first_name}'.encode(),
            confidence_score=round(random.uniform(0.85, 0.98), 2),
            algorithm_version='FaceNet_v1.0'
        )
        db.session.add(biometric)
    
    # Create Authentication Logs
    locations = ['Main Entrance', 'Security Office', 'Finance Dept', 'HR Office']
    for i in range(15):
        employee = random.choice(Employee.query.all())
        result = random.choice(['SUCCESS', 'FAILED'])
        log = AuthenticationLog(
            employee_id=employee.employee_id,
            result=result,
            confidence_score=round(random.uniform(0.60, 0.95), 2),
            failure_reason='Low confidence' if result == 'FAILED' else None,
            device_location=random.choice(locations),
            processing_time_ms=random.randint(800, 1500),
            attempt_timestamp=datetime.utcnow() - timedelta(days=random.randint(0, 5))
        )
        db.session.add(log)
    
    db.session.commit()
    print("✅ Sample data created successfully!")