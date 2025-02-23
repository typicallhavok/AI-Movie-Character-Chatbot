from pymongo import MongoClient
from datetime import datetime
import uuid

# Initialize MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client.dh_users
collection = db.history

def create_chat_window(user_id: str) -> str:
    """
    Create a new chat window document
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        str: Chat window ID
    """
    chat_window = {
        "chat_id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "messages": []
    }
    
    collection.insert_one(chat_window)
    return chat_window["chat_id"]

def add_message(chat_id: str, message: str, response: str) -> bool:
    """
    Add a message and its response to a chat window
    
    Args:
        chat_id: Chat window identifier
        message: User's message
        response: System response
        
    Returns:
        bool: True if successful, False otherwise
    """
    message_data = {
        "message_id": str(uuid.uuid4()),
        "message": message,
        "response": response,
        "timestamp": datetime.now()
    }
    
    result = collection.update_one(
        {"chat_id": chat_id},
        {
            "$push": {"messages": message_data},
            "$set": {"updated_at": datetime.now()}
        }
    )
    
    return result.modified_count > 0

def get_chat_history(chat_id: str) -> list:
    """
    Retrieve all messages from a chat window
    
    Args:
        chat_id: Chat window identifier
        
    Returns:
        list: List of messages in the chat window
    """
    chat = collection.find_one({"chat_id": chat_id})
    return chat["messages"] if chat else []

def get_user_chats(user_id: str) -> list:
    """
    Retrieve all chat windows for a user
    
    Args:
        user_id: User identifier
        
    Returns:
        list: List of chat windows
    """
    return list(collection.find({"user_id": user_id}))

def delete_chat(chat_id: str) -> bool:
    """
    Delete a chat window
    
    Args:
        chat_id: Chat window identifier
        
    Returns:
        bool: True if successful, False otherwise
    """
    result = collection.delete_one({"chat_id": chat_id})
    return result.deleted_count > 0