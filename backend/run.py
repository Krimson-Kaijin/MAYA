"""Boot MAYA locally:  python backend/run.py"""

import uvicorn

from maya.app import create_app
from maya.config import Config

config = Config.load()
app = create_app(config)

if __name__ == "__main__":
    host = config.get("server.host", "127.0.0.1")
    port = int(config.get("server.port", 8930))
    print(f"\n  MAYA is waking up →  http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
