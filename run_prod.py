"""Production entry point for On Point Finance.

Serves the app with waitress (a production WSGI server) on localhost, with debug
OFF. Use this on the office PC; use run.py only while developing.
"""

from dotenv import load_dotenv

# Load environment variables from .env BEFORE building the app.
load_dotenv()

from app import create_app  # noqa: E402
from waitress import serve  # noqa: E402

# Force the production config (DEBUG off) regardless of FLASK_CONFIG.
app = create_app("prod")

HOST = "127.0.0.1"  # this computer only — not exposed to the network
PORT = 5000

if __name__ == "__main__":
    print(f"On Point Finance is running at http://{HOST}:{PORT}")
    print("Keep this window open while you use the app. Press Ctrl+C to stop.")
    serve(app, host=HOST, port=PORT)
