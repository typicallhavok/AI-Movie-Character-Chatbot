from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import requests
from dotenv import load_dotenv
import os

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(os.getenv("PINECONE_API_KEY"))
index = pc.Index(host="https://baai-n5yfgj0.svc.aped-4627-b74a.pinecone.io")
HF_API_KEY = os.getenv("HF_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/BAAI/bge-large-en-v1.5"
headers = {"Authorization": f"Bearer {HF_API_KEY}"}

def get_embedding(text):
    payload = {"inputs": text}
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

def get_context(query, top_k=1):

    vector = get_embedding(query)
    if type(vector) is not list:
        model = SentenceTransformer('BAAI/bge-large-en-v1.5')
        vector = model.encode(query, normalize_embeddings=True)

    document=index.query(
            namespace="movie_dialogues",
            vector=vector.tolist() if type(vector) is not list else vector,
            top_k=top_k,
            include_metadata=True
        )
    return document

# if __name__ == "__main__":
#     query = "DAWSON kneels down by the bed, puts his hand on SANTIAGO'S"
#     context = get_context(query)
#     print(context)

