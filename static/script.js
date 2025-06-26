// Facial Recognition System JavaScript

function simulateAuthentication(employeeId) {
    const resultDiv = document.getElementById('authResult');
    
    fetch('/simulate_auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_id: employeeId })
    })
    .then(response => response.json())
    .then(data => {
        displayAuthResult(data);
    })
    .catch(error => {
        console.error('Authentication error:', error);
    });
}

function displayAuthResult(data) {
    const resultDiv = document.getElementById('authResult');
    const alertClass = data.result === 'SUCCESS' ? 'alert-success' : 'alert-danger';
    const icon = data.result === 'SUCCESS' ? '✅' : '❌';
    
    resultDiv.innerHTML = `
        <div class="alert ${alertClass}">
            <h5>${icon} Authentication ${data.result}</h5>
            <p><strong>Employee:</strong> ${data.employee_name}</p>
            <p><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(1)}%</p>
            <p><strong>Processing Time:</strong> ${data.processing_time}ms</p>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Facial Recognition System loaded');
});