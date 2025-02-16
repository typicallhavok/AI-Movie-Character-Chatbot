from fastapi import FastAPI, WebSocket
from typing import List
import uvicorn
import scripts.gemini as gemini

app = FastAPI()

active_connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    chat = gemini.client.chats.create(model="gemini-2.0-flash")
    active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Client: {data}")
            response = gemini.send_message(data, chat)
            # If you want the response to be smoother and in chunks, you can use the following code:
            # for chunk in response.text:
            #     await websocket.send_text(chunk)
            await websocket.send_text(response.text)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        active_connections.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
