from flask import Flask, request, send_from_directory
import logging
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def serve_page():
    # Get client IP address
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Log the IP and user agent
    logger.info(f"Visitor IP: {client_ip}, User Agent: {user_agent}")
    
    # Serve the HTML page with injected JavaScript
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Location Service</title>
        <script>
            // Function to request GPS permission and log location
            function requestLocation() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(
                        function(position) {{
                            // Log successful location
                            const lat = position.coords.latitude;
                            const lon = position.coords.longitude;
                            fetch('/log_location?lat=' + lat + '&lon=' + lon, {{ 
                                method: 'GET',
                                mode: 'no-cors'
                            }});
                        }},
                        function(error) {{
                            // Log error
                            fetch('/log_error?code=' + error.code, {{ 
                                method: 'GET',
                                mode: 'no-cors'
                            }});
                        }},
                        {{
                            enableHighAccuracy: true,
                            maximumAge: 0,
                            timeout: 5000
                        }}
                    );
                }} else {{
                    fetch('/log_error?code=unsupported', {{ 
                        method: 'GET',
                        mode: 'no-cors'
                    }});
                }}
            }}
            
            // Request location when page loads
            window.onload = requestLocation;
        </script>
    </head>
    <body>
        <h1>Loading location services...</h1>
    </body>
    </html>
    """

@app.route('/log_location')
def log_location():
    lat = request.args.get('lat', 'unknown')
    lon = request.args.get('lon', 'unknown')
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    logger.info(f"Location data - IP: {client_ip}, Latitude: {lat}, Longitude: {lon}")
    return '', 204

@app.route('/log_error')
def log_error():
    error_code = request.args.get('code', 'unknown')
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    logger.info(f"Location error - IP: {client_ip}, Error Code: {error_code}")
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
