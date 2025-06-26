from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from models import db, Role, Employee, BiometricData, AuthenticationLog
from database import init_database
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'facial-recognition-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///facial_recognition.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def dashboard():
    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(is_active=True).count()
    today_auths = AuthenticationLog.query.filter(
        AuthenticationLog.attempt_timestamp >= datetime.utcnow().date()
    ).count()
    recent_logs = AuthenticationLog.query.order_by(
        AuthenticationLog.attempt_timestamp.desc()
    ).limit(5).all()
    
    total_attempts = AuthenticationLog.query.count()
    successful_attempts = AuthenticationLog.query.filter_by(result='SUCCESS').count()
    success_rate = round((successful_attempts / total_attempts) * 100, 1) if total_attempts > 0 else 0
    
    return render_template('dashboard.html', 
                         total_employees=total_employees,
                         active_employees=active_employees,
                         today_auths=today_auths,
                         success_rate=success_rate,
                         recent_logs=recent_logs)

@app.route('/employees')
def employees():
    employees_list = db.session.query(Employee, Role).join(Role).all()
    roles = Role.query.all()
    return render_template('employees.html', employees=employees_list, roles=roles)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    try:
        new_employee = Employee(
            role_id=request.form['role_id'],
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form['email'],
            department=request.form['department']
        )
        db.session.add(new_employee)
        db.session.commit()
        
        biometric = BiometricData(
            employee_id=new_employee.employee_id,
            face_encoding=f'ENCODING_{new_employee.first_name}'.encode(),
            confidence_score=round(random.uniform(0.85, 0.95), 2),
            algorithm_version='FaceNet_v1.0'
        )
        db.session.add(biometric)
        db.session.commit()
        
        flash(f'Employee {new_employee.full_name} added successfully!', 'success')
    except Exception as e:
        flash('Error adding employee. Email might already exist.', 'error')
        db.session.rollback()
    
    return redirect(url_for('employees'))

@app.route('/authentication')
def authentication():
    employees_list = Employee.query.filter_by(is_active=True).all()
    return render_template('authentication.html', employees=employees_list)

@app.route('/simulate_auth', methods=['POST'])
def simulate_authentication():
    employee_id = request.json.get('employee_id')
    employee = Employee.query.get(employee_id)
    
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404
    
    confidence = round(random.uniform(0.60, 0.95), 2)
    result = 'SUCCESS' if confidence > 0.75 else 'FAILED'
    processing_time = random.randint(800, 1800)
    
    auth_log = AuthenticationLog(
        employee_id=employee_id,
        result=result,
        confidence_score=confidence,
        failure_reason='Low confidence score' if result == 'FAILED' else None,
        device_location='Prototype Simulator',
        processing_time_ms=processing_time
    )
    
    db.session.add(auth_log)
    if result == 'SUCCESS':
        employee.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'result': result,
        'employee_name': employee.full_name,
        'confidence': confidence,
        'processing_time': processing_time,
        'timestamp': auth_log.attempt_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/logs')
def logs():
    logs_list = db.session.query(AuthenticationLog, Employee).join(Employee).order_by(
        AuthenticationLog.attempt_timestamp.desc()
    ).limit(50).all()
    return render_template('logs.html', logs=logs_list)

if __name__ == '__main__':
    init_database(app)
    print("🔒 Facial Recognition System Starting...")
    print("📊 Database: SQLite")
    print("🌐 URL: http://localhost:5000")
    app.run(debug=True, port=5000)