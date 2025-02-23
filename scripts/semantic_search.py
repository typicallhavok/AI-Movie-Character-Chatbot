import os
import google.genai as genai
import chromadb
from dotenv import load_dotenv
import gemini

load_dotenv()

# Initialize ChromaDB
client = chromadb.PersistentClient(path="../chroma")
collection = client.get_or_create_collection("movie_scripts")

def retrieve_relevant_dialogues(query, n_results=5):
    """
    Retrieve the most relevant dialogues based on a query using similarity search.
    
    Args:
        query (str): The query text to search for
        n_results (int): Number of results to return
        
    Returns:
        list: List of relevant dialogue entries with metadata
    """

    # Generate embedding for the query
    query_embedding = gemini.get_gemini_embedding(query)
    
    # Perform similarity search in ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["metadatas", "distances"]
    )
    
    # Format the results
    formatted_results = []
    if results and results["metadatas"] and len(results["metadatas"]) > 0:
        metadatas = results["metadatas"][0]
        distances = results["distances"][0] if "distances" in results else [None] * len(metadatas)
        
        for i, metadata in enumerate(metadatas):
            formatted_results.append({
                "title": metadata.get("title", "Unknown"),
                "speaker": metadata.get("speaker", "Unknown"),
                "dialogue": metadata.get("dialogue", ""),
                "similarity_score": 1 - distances[i] if distances[i] is not None else None
            })
    
    return formatted_results

# # Example usage
# def print_search_results(query):
#     print(f"\nSearch query: '{query}'")
#     print("-" * 80)
    
#     results = retrieve_relevant_dialogues(query)
    
#     if not results:
#         print("No relevant dialogues found.")
#         return
    
#     for i, result in enumerate(results):
#         print(f"Result #{i+1} (Similarity: {result['similarity_score']:.4f})")
#         print(f"Movie: {result['title']}")
#         print(f"Speaker: {result['speaker']}")
#         print(f"Dialogue: {result['dialogue'][:150]}..." if len(result['dialogue']) > 150 else result['dialogue'])
#         print("-" * 80)

# if __name__ == "__main__":
#     # Process the dialogues first (your existing code)
#     # store_json_dialogues_in_chroma("../movie_scripts", batch_size=20)
    
#     # Then perform some example searches
#     print("\n===== TESTING SEARCH FUNCTIONALITY =====\n")
#     example_queries = [
#         "You are interested in Bianca?",
#         "Yacco shoots Malee the look of death.",
#     ]
    
#     for query in example_queries:
#         print_search_results(query)