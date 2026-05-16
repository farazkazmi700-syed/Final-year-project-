from backend.app import create_app

# Use the full backend Flask application for Vercel routing.
app = create_app()
