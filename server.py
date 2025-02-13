from fastapi import FastAPI, WebSocket
from typing import List
import uvicorn

app = FastAPI()

active_connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Client: {data}")
            response = f"Server received: {data} and f u"
            await websocket.send_text(response)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        active_connections.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
