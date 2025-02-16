import chromadb
from chromadb.utils import embedding_functions
import json
import re
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def extract_character_dialogues(script_content):
    """Extract dialogues per character from script"""
    dialogues = {}
    pattern = r'\n\s+([A-Z][A-Z\s]+)\n\s+(.*?)(?=\n\s+[A-Z][A-Z\s]+\n|\Z)'
    matches = re.finditer(pattern, script_content)
    
    for match in matches:
        character = match.group(1).strip()
        dialogue = match.group(2).strip()
        
        if '(' in character or ')' in character:
            continue
            
        if character not in dialogues:
            dialogues[character] = []
        dialogues[character].append(dialogue)
    
    return dialogues

def init_mongo():
    """Initialize MongoDB connection"""
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['movie_dialogues']
    return db['characters']

def init_vector_store():
    """Initialize ChromaDB client and collection"""
    chroma_client = chromadb.PersistentClient(path="../chroma_db")
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    collection = chroma_client.get_or_create_collection(
        name="movie_dialogues",
        embedding_function=embedding_function
    )
    return collection

def store_in_mongodb(movie_data, mongo_collection):
    """Store dialogues in MongoDB"""
    movie_title = movie_data['movie_title']
    
    if mongo_collection.find_one({"movie_title": movie_title}):
        print(f"MongoDB: Dialogues for {movie_title} already stored")
        return
    
    dialogues = extract_character_dialogues(movie_data['content'])
    
    document = {
        "movie_title": movie_title,
        "characters": {}
    }
    
    for character, lines in dialogues.items():
        document["characters"][character] = {
            "dialogues": lines,
            "total_lines": len(lines)
        }
    
    mongo_collection.insert_one(document)
    print(f"MongoDB: Stored {len(dialogues)} characters for {movie_title}")

def store_dialogues(movie_data, vector_collection, mongo_collection):
    """Store dialogues in both ChromaDB and MongoDB"""
    store_in_mongodb(movie_data, mongo_collection)
    
    movie_title = movie_data['movie_title']
    if len(vector_collection.get(where={"movie_title": movie_title})["ids"]) > 0:
        print(f"ChromaDB: Dialogues for {movie_title} already stored")
        return 0
        
    dialogues = extract_character_dialogues(movie_data['content'])
    
    for character, lines in dialogues.items():
        ids = [f"{movie_title}_{character}_{i}" for i in range(len(lines))]
        
        metadatas = [{
            "movie_title": movie_title,
            "character": character,
            "line_number": i
        } for i in range(len(lines))]
        
        vector_collection.add(
            documents=lines,
            ids=ids,
            metadatas=metadatas
        )
    
    return len(dialogues)

if __name__ == "__main__":
    vector_collection = init_vector_store()
    mongo_collection = init_mongo()
    
    for filename in os.listdir('../movie_scripts'):
        if filename.endswith('.json'):
            with open(f'../movie_scripts/{filename}', 'r', encoding='utf-8') as f:
                movie_data = json.load(f)
                num_characters = store_dialogues(
                    movie_data, 
                    vector_collection,
                    mongo_collection
                )
                print(f"Processed {filename}")
