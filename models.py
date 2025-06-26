from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Role(db.Model):
    __tablename__ = 'role'
    
    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    security_level = db.Column(db.Integer, nullable=False)
    max_attempts = db.Column(db.Integer, default=3)
    can_enroll_others = db.Column(db.Boolean, default=False)
    
    employees = db.relationship('Employee', backref='role', lazy=True)
    
    def __repr__(self):
        return f'<Role {self.role_name}>'

class Employee(db.Model):
    __tablename__ = 'employee'
    
    employee_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.role_id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(50))
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    biometric_data = db.relationship('BiometricData', backref='employee', lazy=True)
    authentication_logs = db.relationship('AuthenticationLog', backref='employee', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class BiometricData(db.Model):
    __tablename__ = 'biometric_data'
    
    biometric_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'), nullable=False)
    face_encoding = db.Column(db.LargeBinary)
    confidence_score = db.Column(db.Float)
    algorithm_version = db.Column(db.String(50))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class AuthenticationLog(db.Model):
    __tablename__ = 'authentication_log'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'), nullable=False)
    attempt_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    result = db.Column(db.String(20), nullable=False)
    confidence_score = db.Column(db.Float)
    failure_reason = db.Column(db.String(100))
    device_location = db.Column(db.String(100))
    processing_time_ms = db.Column(db.Integer)