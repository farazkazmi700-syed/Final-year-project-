from backend.app import create_app
from backend.config import Config

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.APP_PORT, debug=False, use_reloader=False)
