from fastapi import FastAPI, WebSocket, Request, HTTPException
from typing import List
import uvicorn
import scripts.gemini as gemini
import scripts.searchv2 as searchv2
from google.genai import types
import scripts.chat_history as chat_history
from pydantic import BaseModel

class SearchRequest(BaseModel):
    search_query: str
    top_k: int

app = FastAPI()

sys_inst = """You are a character in a movie, you will be provided with the movie title, context, and a prompt. You have to respond to the prompt as if you
were the character mimicing the character's personality in the movie talking to another character. You can use the context and movie title to find the movie 
and the movie script to understand the situation and respond accordingly.
"""

active_connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    chat = gemini.client.chats.create(model="gemini-2.0-flash",config=types.GenerateContentConfig(
        system_instruction=sys_inst))
    active_connections.append(websocket)

    websocket.send_text("Enter username: ")
    username = await websocket.receive_text()
    chat_window_id = chat_history.create_chat_window(username)
    movie_title = ""
    context = ""
    try:
        while True:
            query = await websocket.receive_text()
            print(f"Client: {query}")
            try:
                if not movie_title or not context:
                    search_result = searchv2.get_context(query)
                    if search_result["matches"]:
                        context = search_result["matches"][0]["metadata"]["text"]
                        movie_title = search_result["matches"][0]["metadata"]["movie_title"]

                message = f"""
                            movie title: {movie_title}
                            context: {context}
                            user message: {query}
                            """
                gem_response = gemini.send_message(message, chat)

                # If you want the response to be smoother and in chunks, you can use the following code:
                # for chunk in response.text:
                #     await websocket.send_text(chunk)
            except Exception as err:
                websocket.send_text(str(err))

            chat_history.add_message(chat_window_id, message, gem_response.text)
            await websocket.send_text(gem_response.text)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        active_connections.remove(websocket)

@app.post("/search_dialogue")
async def search_dialogue(request: SearchRequest):
    if not request.search_query:
        raise HTTPException(status_code=400, detail="search_query is required")
    
    response = searchv2.get_context(request.search_query, request.top_k)
    return {"response": response}

@app.get("/get_user_chats")
async def get_user_chats_route(user_id: str):
    return chat_history.get_user_chats(user_id)

@app.get("/delete_chat")
async def delete_chat_route(chat_id: str):
    return chat_history.delete_chat(chat_id)

@app.get("/get_chat_history")
async def get_chat_history_route(chat_id: str):
    return chat_history.get_chat_history(chat_id)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
