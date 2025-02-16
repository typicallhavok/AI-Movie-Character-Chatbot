import chromadb
from chromadb.utils import embedding_functions
from typing import Dict, List, Tuple

def search_character_dialogues(query: str, character_name: str = None, movie_title: str = None, k: int = 5) -> List[Dict]:
    """Search for relevant character dialogues in the database"""
    chroma_client = chromadb.PersistentClient(path="../chroma_db")
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    collection = chroma_client.get_collection(
        name="movie_dialogues",
        embedding_function=embedding_function
    )
    
    where_clause = None
    if character_name and movie_title:
        where_clause = {
            "$and": [
                {"character": {"$eq": character_name}},
                {"movie_title": {"$eq": movie_title}}
            ]
        }
    elif character_name:
        where_clause = {"character": {"$eq": character_name}}
    elif movie_title:
        where_clause = {"movie_title": {"$eq": movie_title}}
    
    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where_clause
    )
    
    matches = []
    for i in range(len(results['ids'][0])):
        match = {
            'dialogue': results['documents'][0][i],
            'movie': results['metadatas'][0][i]['movie_title'],
            'character': results['metadatas'][0][i]['character'],
            'line_number': results['metadatas'][0][i]['line_number']
        }
        matches.append(match)
    
    return matches

# if __name__ == "__main__":
#     print("Testing dialogue search...")
    
#     # Test cases
#     test_queries = [
#         # 10 Things I Hate About You tests
#         {
#             "query": "I hate",  # Kat's famous poem
#             "character": "Kat",
#             "movie": "10 Things I Hate About You",
#             "expected": "Should return Kat's poem dialogue about things she hates"
#         },
#         {
#             "query": "dating",  # Cameron's discussions about dating Bianca
#             "character": "Cameron",
#             "movie": "10 Things I Hate About You",
#             "expected": "Should return Cameron's dialogues about wanting to date Bianca"
#         },
#         {
#             "query": "party",  # General party scene dialogues
#             "movie": "10 Things I Hate About You",
#             "expected": "Should return various character dialogues from the party scene"
#         },
        
#         # Movie "12" tests
#         {
#             "query": "jury",  # Discussions in jury room
#             "movie": "12",
#             "expected": "Should return dialogues from jury deliberations"
#         },
#         {
#             "query": "guilty",  # Arguments about guilt
#             "movie": "12",
#             "expected": "Should return discussions about the defendant's guilt"
#         },
        
#         # Cross-movie searches
#         {
#             "query": "angry",  # Emotional moments in both movies
#             "expected": "Should return angry dialogues from both movies"
#         }
#     ]
    
#     for test in test_queries:
#         print(f"\n{'='*50}")
#         print(f"Test Query: {test['query']}")
#         print(f"Expected: {test['expected']}")
#         print(f"Filters: {', '.join(f'{k}: {v}' for k, v in test.items() if k not in ['query', 'expected'])}")
        
#         results = search_character_dialogues(
#             query=test["query"],
#             character_name=test.get("character"),
#             movie_title=test.get("movie")
#         )
        
#         print(f"\nFound {len(results)} matches:")
#         for result in results:
#             print(f"\nMovie: {result['movie']}")
#             print(f"Character: {result['character']}")
#             print(f"Dialogue: {result['dialogue']}")
#         print(f"{'='*50}")