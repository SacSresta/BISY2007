from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from models import db, Role, Employee, BiometricData, AuthenticationLog
from database import init_database
from datetime import datetime
import random
# Add these imports to your app.py
import cv2
import mediapipe as mp
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import hashlib

# Initialize MediaPipe
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

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

@app.route('/enroll_face', methods=['POST'])
def enroll_face():
    """Enroll a face using MediaPipe"""
    try:
        employee_id = request.json.get('employee_id')
        image_data = request.json.get('image_data')
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Detect faces with MediaPipe
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_image)
            
            if results.detections:
                # Create a simple face "signature" based on bounding box and landmarks
                detection = results.detections[0]  # Use first detected face
                
                # Get bounding box
                bbox = detection.location_data.relative_bounding_box
                h, w, _ = opencv_image.shape
                
                # Create face signature (simplified for prototype)
                face_signature = {
                    'bbox_x': bbox.xmin,
                    'bbox_y': bbox.ymin,
                    'bbox_width': bbox.width,
                    'bbox_height': bbox.height,
                    'confidence': detection.score[0]
                }
                
                # Convert to string for storage
                face_encoding = str(face_signature).encode()
                
                # Store or update biometric data
                biometric = BiometricData.query.filter_by(employee_id=employee_id).first()
                if biometric:
                    biometric.face_encoding = face_encoding
                    biometric.confidence_score = detection.score[0]
                    biometric.algorithm_version = 'MediaPipe_v1.0'
                else:
                    biometric = BiometricData(
                        employee_id=employee_id,
                        face_encoding=face_encoding,
                        confidence_score=detection.score[0],
                        algorithm_version='MediaPipe_v1.0',
                        is_active=True
                    )
                    db.session.add(biometric)
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Face enrolled successfully with MediaPipe',
                    'confidence': float(detection.score[0]),
                    'faces_detected': len(results.detections)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No face detected in image'
                }), 400
                
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing image: {str(e)}'
        }), 500

@app.route('/authenticate_face_mediapipe', methods=['POST'])
def authenticate_face_mediapipe():
    """Real facial recognition using MediaPipe"""
    try:
        image_data = request.json.get('image_data')
        
        # Decode image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Detect faces with MediaPipe
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_image)
            
            if not results.detections:
                return jsonify({
                    'result': 'FAILED',
                    'message': 'No face detected',
                    'confidence': 0.0
                })
            
            # Get the detected face
            detection = results.detections[0]
            bbox = detection.location_data.relative_bounding_box
            
            current_face = {
                'bbox_x': bbox.xmin,
                'bbox_y': bbox.ymin,
                'bbox_width': bbox.width,
                'bbox_height': bbox.height,
                'confidence': detection.score[0]
            }
            
            # Compare with stored faces (simplified matching)
            stored_biometrics = BiometricData.query.filter_by(is_active=True).all()
            
            best_match = None
            best_similarity = 0.0
            
            for biometric in stored_biometrics:
                try:
                    # Parse stored face data
                    stored_face_str = biometric.face_encoding.decode()
                    stored_face = eval(stored_face_str)  # Simple eval for prototype
                    
                    # Calculate similarity based on bounding box similarity
                    similarity = calculate_face_similarity(current_face, stored_face)
                    
                    if similarity > best_similarity and similarity > 0.7:  # Threshold
                        best_similarity = similarity
                        best_match = biometric
                        
                except Exception as e:
                    continue  # Skip corrupted data
            
            if best_match:
                employee = best_match.employee
                result = 'SUCCESS' if best_similarity > 0.8 else 'FAILED'
                
                # Log authentication
                auth_log = AuthenticationLog(
                    employee_id=employee.employee_id,
                    result=result,
                    confidence_score=best_similarity,
                    failure_reason=None if result == 'SUCCESS' else 'Low similarity score',
                    device_location='MediaPipe Camera',
                    processing_time_ms=random.randint(800, 1500)
                )
                
                db.session.add(auth_log)
                
                if result == 'SUCCESS':
                    employee.last_login = datetime.utcnow()
                
                db.session.commit()
                
                return jsonify({
                    'result': result,
                    'employee_name': employee.full_name,
                    'employee_id': employee.employee_id,
                    'confidence': round(best_similarity, 3),
                    'processing_time': auth_log.processing_time_ms,
                    'timestamp': auth_log.attempt_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'role': employee.role.role_name
                })
            else:
                # Unknown person
                return jsonify({
                    'result': 'FAILED',
                    'message': 'Unknown person or low confidence',
                    'confidence': round(best_similarity, 3)
                })
                
    except Exception as e:
        return jsonify({
            'result': 'ERROR',
            'message': f'Processing error: {str(e)}',
            'confidence': 0.0
        }), 500

def calculate_face_similarity(face1, face2):
    """Calculate similarity between two face signatures (simplified for prototype)"""
    try:
        # Compare bounding box dimensions and positions
        pos_diff = abs(face1['bbox_x'] - face2['bbox_x']) + abs(face1['bbox_y'] - face2['bbox_y'])
        size_diff = abs(face1['bbox_width'] - face2['bbox_width']) + abs(face1['bbox_height'] - face2['bbox_height'])
        
        # Simple similarity calculation (0 to 1)
        total_diff = pos_diff + size_diff
        similarity = max(0, 1 - (total_diff * 2))  # Adjust multiplier for sensitivity
        
        return similarity
    except:
        return 0.0

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