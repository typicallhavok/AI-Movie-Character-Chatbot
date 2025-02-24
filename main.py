from fastapi import FastAPI, WebSocket, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
import uvicorn
import scripts.gemini as gemini
import scripts.searchv2 as searchv2
from google.genai import types
import scripts.chat_history as chat_history
from pydantic import BaseModel
import redis
import json
import asyncio
import time
from pinecone import QueryResponse
from bson import ObjectId
from datetime import datetime

class SearchRequest(BaseModel):
    search_query: str
    top_k: int = 5

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
if redis_client.ping():
    print("Connected to Redis!")
CACHE_EXPIRATION = 3600

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Movie Character API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sys_inst = """You are a character in a movie, you will be provided with the movie title, context, and a prompt. You have to respond to the prompt as if you
were the character mimicing the character's personality in the movie talking to another character. You can use the context and movie title to find the movie 
and the movie script to understand the situation and respond accordingly.
"""

active_connections: List[WebSocket] = []


@app.get("/")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

def serialize_mongo_document(document):
    """Recursively convert ObjectId and datetime fields in MongoDB documents to JSON serializable formats."""
    if isinstance(document, list):
        return [serialize_mongo_document(doc) for doc in document]
    elif isinstance(document, dict):
        return {key: serialize_mongo_document(value) for key, value in document.items()}
    elif isinstance(document, ObjectId):
        return str(document)
    elif isinstance(document, datetime):
        return document.isoformat()
    return document

def convert_doc(doc):
    """Convert `_id` and `datetime` fields to string format."""
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


def get_cached_context(query: str) -> Optional[dict]:
    cache_key = f"search_context:{query}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None

def cache_context(query: str, result) -> None:
    """
    Caches the search result in Redis for future use.

    :param query: The search query used to fetch results.
    :param result: The search result (may need conversion).
    """
    cache_key = f"search_context:{query}"
    
    try:

        if hasattr(result, "to_dict"):
            result = result.to_dict()
        elif isinstance(result, QueryResponse):
            result = json.loads(json.dumps(result, default=lambda o: o.__dict__))

        json_result = json.dumps(result, ensure_ascii=False)

        redis_client.setex(cache_key, CACHE_EXPIRATION, json_result)

    except TypeError as e:
        print(f"ERROR: Failed to serialize result to JSON: {e}")
    except redis.RedisError as e:
        print(f"ERROR: Redis error occurred: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    chat = gemini.client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=sys_inst)
    )
    active_connections.append(websocket)

    await websocket.send_text("Enter username: ")
    username = await websocket.receive_text()
    chat_window_id = chat_history.create_chat_window(username)
    movie_title = ""
    context = ""
    message = ""
    gem_response = None
    await websocket.send_text("Enter any movie dialogue")
    try:
        while True:
            query = await websocket.receive_text()
            print(f"Client: {query}")
            try:
                if not movie_title or not context:
                    cached_result = get_cached_context(query)
                    
                    if cached_result:
                        search_result = cached_result
                    else:
                        search_result = await asyncio.to_thread(searchv2.get_context, query)
                        if search_result["matches"]:
                            cache_context(query, search_result)
                    
                    if search_result["matches"]:
                        context = search_result["matches"][0]["metadata"]["text"]
                        movie_title = search_result["matches"][0]["metadata"]["movie_title"]
                if movie_title:
                    await websocket.send_text(f"movie: {movie_title}")
                message = f"""
                            movie title: {movie_title}
                            context: {context}
                            user message: {query}
                            """
                gem_response = await asyncio.to_thread(gemini.send_message, message, chat)
            except Exception as err:
                await websocket.send_text(f"Error: {str(err)}")

            chat_history.add_message(chat_window_id, message, gem_response.text)
            await websocket.send_text(gem_response.text)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        active_connections.remove(websocket)

@app.post("/search_dialogue")
async def search_dialogue(request: SearchRequest, background_tasks: BackgroundTasks, request_obj: Request):
    if not request.search_query:
        raise HTTPException(status_code=400, detail="search_query is required")

    cached_result = get_cached_context(request.search_query)
    if cached_result:
        return {"response": cached_result, "source": "cache"}

    response = await asyncio.to_thread(searchv2.get_context, request.search_query, request.top_k)

    if response is None:
        return {"response": "No results found", "source": "live"}

    try:
        response_dict = json.loads(json.dumps(response, default=str))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Serialization error: {str(e)}")

    background_tasks.add_task(cache_context, request.search_query, response_dict)

    return {"response": response_dict, "source": "live"}


@app.get("/get_user_chats")
async def get_user_chats_route(user_id: str):
    cache_key = f"user_chats:{user_id}"

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        result = await asyncio.to_thread(chat_history.get_user_chats, user_id)

        if result:
            result = serialize_mongo_document(result)  # Ensure datetime conversion
            redis_client.setex(cache_key, 300, json.dumps(result))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete_chat")
async def delete_chat_route(chat_id: str):
    """Deletes a chat and clears related cache."""
    try:
        result = await asyncio.to_thread(chat_history.delete_chat, chat_id)

        pattern = "user_chats:*"
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_chat_history")
async def get_chat_history_route(chat_id: str):
    cache_key = f"chat_history:{chat_id}"

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        result = await asyncio.to_thread(chat_history.get_chat_history, chat_id)

        if result:
            result = serialize_mongo_document(result)  # Ensure datetime conversion
            redis_client.setex(cache_key, 300, json.dumps(result))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_cache")
async def clear_cache():
    """Clears the Redis cache."""
    try:
        redis_client.flushdb()
        return {"status": "Cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)