"""Entry point for development.

Loads the .env file, builds the app via the factory, and starts the built-in
development server. (In Phase 9 we add a production launcher using waitress.)
"""

from dotenv import load_dotenv

# Load environment variables from .env BEFORE building the app.
load_dotenv()

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    # 127.0.0.1 = this computer only. Not exposed to the network.
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
