# AI Movie Character Chatbot

Chatbot which detects and mimics a character with provided context

# Routes

```
GET "/" : health check
WebSocket "/ws" : websocket
POST "/search_dialogue" : Retrieve context from vector database
GET "/get_user_chats" : get previous user chats
GET "/delete_chat" : Delete a chat
GET "/get_chat_history" : Get chat history
```

# Setup locally

store the environment variables of gemini, huggingface, pinecone in .env and run these commands

```
pip install -r requirements.txt
uvicorn main:app
```

# Movies

Check movies.txt for all the movies that are available to choose from
 
