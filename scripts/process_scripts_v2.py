import os
import json
import re
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor
import torch

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Initialize Pinecone client
pc = Pinecone(PINECONE_API_KEY)
index = pc.Index(host="https://baai-n5yfgj0.svc.aped-4627-b74a.pinecone.io")

# Load Sentence Transformer model (CUDA if available)

model = SentenceTransformer("BAAI/bge-large-en-v1.5",device="cuda")

def clean_text(text: str) -> str:
    """Cleans script text to improve embeddings quality."""
    text = re.sub(r'\r\n\s+\r\n', '\r\n\r\n', text)  # Remove extra whitespace
    text = re.sub(r' +', ' ', text)  # Remove multiple spaces
    text = re.sub(r'\s+([A-Z]+)\s+', r'\n\1: ', text)  # Format character names
    text = re.sub(r'\s+([.,!?])', r'\1', text)  # Fix punctuation spacing
    text = re.sub(r'\s+INT\.\s+', '\nINT. ', text)  # Standardize scene headings
    text = re.sub(r'\s+EXT\.\s+', '\nEXT. ', text)
    text = re.sub(r'\n\s*\d+\.\s*\n', '\n', text)  # Remove page numbers
    return text.strip()

def load_and_chunk_scripts(directory_path: str, chunk_size: int = 1000) -> List[Dict]:
    """Loads movie scripts, cleans them, and splits into overlapping chunks."""
    all_chunks = []
    chunk_id = 0
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            content = clean_text(script_data['content'])
            movie_title = script_data['movie_title']

            # Split content into overlapping chunks
            for i in range(0, len(content), chunk_size // 2):
                chunk = content[i:i + chunk_size]
                if len(chunk) >= 50:  # Skip very small chunks
                    all_chunks.append({
                        'id': f"{movie_title}_{chunk_id}",
                        'text': chunk,
                        'movie_title': movie_title
                    })
                    chunk_id += 1
                    
    return all_chunks


def process_batch(batch: List[Dict]) -> List[Dict]:
    """Generates embeddings for a batch efficiently on GPU."""
    with torch.no_grad():  # Disables gradient calculation
        embeddings = model.encode(
            [d['text'] for d in batch], 
            normalize_embeddings=True,
            convert_to_tensor=True,  # Keep tensors for efficiency
            show_progress_bar=False  # Disable tqdm inside encode
        ).half()  # Convert to FP16 if supported

    return [
        {
            "id": d['id'],
            "values": e.cpu().tolist(),  # Move tensor to CPU only when needed
            "metadata": {"text": d['text'], "movie_title": d['movie_title']}
        }
        for d, e in zip(batch, embeddings)
    ]


# def process_chunks_parallel(chunks: List[Dict], batch_size: int = 128, num_workers: int =8 ):
#     """Processes chunks in parallel using multiple threads."""
#     vectors = []
#     batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]
    
#     with ThreadPoolExecutor(max_workers=num_workers) as executor:
#         for batch_vectors in tqdm(executor.map(process_batch, batches), total=len(batches)):
#             index.upsert(vectors=batch_vectors, namespace="movie_dialogues")

def process_chunks_parallel(chunks: List[Dict], batch_size: int = 128):
    """Processes chunks efficiently using optimized GPU and upsert settings."""
    vectors = []

    for i in tqdm(range(0, len(chunks), batch_size), total=len(chunks) // batch_size, desc="Processing batches"):
        batch = chunks[i:i + batch_size]
        vectors.extend(process_batch(batch))  # Fast GPU encoding

    upsert_vectors_parallel(vectors)  # Optimized upsert

def upsert_vectors_parallel(vectors: List[Dict], batch_size: int = 500):
    """Upserts vectors to Pinecone in parallel batches."""
    batches = [vectors[i:i + batch_size] for i in range(0, len(vectors), batch_size)]

    with ThreadPoolExecutor(max_workers=8) as executor:  # Use 8 threads for parallel uploads
        list(tqdm(executor.map(lambda batch: index.upsert(vectors=batch, namespace="movie_dialogues"), batches),
                  total=len(batches), desc="Upserting to Pinecone"))



def search_similar_dialogue(query: str, top_k: int = 5, namespace: str = "movie_scripts") -> List[Dict]:
    """Searches for similar movie dialogues based on input query."""
    query_embedding = model.encode([query], normalize_embeddings=True)[0].tolist()

    results = index.query(
        namespace=namespace,
        vector=query_embedding,
        top_k=top_k,
        include_values=True,
        include_metadata=True
    )

    # Return formatted results
    return [
        {
            'score': match['score'],
            'movie_title': match['metadata']['movie_title'],
            'text': match['metadata']['text']
        }
        for match in results['matches']
    ]

def main():
    """Main function to load scripts, generate embeddings, and perform search."""
    print("Loading and chunking scripts...")
    chunks = load_and_chunk_scripts('../movie_scripts')

    print("\nProcessing chunks in parallel and generating embeddings...")
    process_chunks_parallel(chunks)

    # Example search
    query = "What do you hate about me?"
    print("\nSearching for similar dialogues...")
    results = search_similar_dialogue(query=query)

    # Display results
    print("\nSearch Results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Movie: {result['movie_title']}")
        print(f"Score: {result['score']:.3f}")
        print(f"Text: {result['text'][:200]}...")

if __name__ == "__main__":
    main()