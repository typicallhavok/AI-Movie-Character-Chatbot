from pymongo import MongoClient
import os

def get_dialogue_with_context(dialogue_id, context_size=3):
    """
    Retrieve a dialogue with its surrounding context from MongoDB.
    
    Parameters:
    - dialogue_id: The ID of the dialogue to search for
    - context_size: Number of dialogues to include before and after (default: 3)
    
    Returns:
    - Dictionary containing the dialogue and its context
    """
    # Connect to MongoDB
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    db = client.movie_database
    dialogues_collection = db.dialogues
    
    # Get the target dialogue
    target_dialogue = dialogues_collection.find_one({"_id": dialogue_id})
    
    if not target_dialogue:
        return
    
    # Extract movie title and sequence number
    try:
        movie_title, seq_num_str = dialogue_id.rsplit('_', 1)
        seq_num = int(seq_num_str)
    except ValueError:
        return {"error": "Invalid dialogue_id format. Expected format: movie_title_number"}
    
    # Calculate the range for context
    start_seq = max(0, seq_num - context_size)
    end_seq = seq_num + context_size + 1  # +1 because range is exclusive
    
    # Generate IDs for the context dialogues
    context_ids = [f"{movie_title}_{i}" for i in range(start_seq, end_seq)]
    
    # Retrieve all context dialogues in order
    context_dialogues = list(dialogues_collection.find(
        {"_id": {"$in": context_ids}},
        {"_id": 1, "speaker": 1, "dialogue": 1}
    ).sort("_id", 1))
    
    # Mark the target dialogue
    for dialogue in context_dialogues:
        dialogue["is_target"] = (dialogue["_id"] == dialogue_id)
    
    return {
        "movie_title": target_dialogue["title"],
        "target_dialogue": {
            "speaker": target_dialogue["speaker"],
            "dialogue": target_dialogue["dialogue"]
        },
        "full_context": context_dialogues
    }

def search_dialogue_by_text(search_text, limit=1, context_size=2):
    """
    Search for dialogues containing specific text and return with context.
    
    Parameters:
    - search_text: Text to search for in dialogues
    - limit: Maximum number of results to return (default: 10)
    - context_size: Number of dialogues to include before and after (default: 2)
    
    Returns:
    - List of dialogues with context
    """
    # Connect to MongoDB
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    db = client.movie_database
    dialogues_collection = db.dialogues
    
    # Create text index if it doesn't exist
    if "dialogue_text" not in dialogues_collection.index_information():
        dialogues_collection.create_index([("dialogue", "text")])
    
    # Find dialogues matching the search text
    dialogue = list(dialogues_collection.find(
        {"$text": {"$search": search_text}},
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]))
    print(f"dialogue: {dialogue[-1]}")

    # Get context for each matching dialogue
    context = get_dialogue_with_context(dialogue["_id"], context_size)
    result = ({
        "movie_title": dialogue["title"],
        "dialogue_id": dialogue["_id"],
        "matching_dialogue": {
            "speaker": dialogue["speaker"],
            "dialogue": dialogue["dialogue"]
        },
        "context": context["full_context"] if "full_context" in context else []
    })
    
    return result

# Example usage
# if __name__ == "__main__":
#     # Example 1: Get context for a specific dialogue
#     result = get_dialogue_with_context("The_Godfather_42")
#     print(f"Context for dialogue from {result['movie_title']}:")
#     for d in result["full_context"]:
#         prefix = ">> " if d.get("is_target") else "   "
#         print(f"{prefix}{d['speaker']}: {d['dialogue'][:60]}...")
    
#     print("\n" + "-"*80 + "\n")
    
#     # Example 2: Search for dialogues by text
#     search_results = search_dialogue_by_text("offer he can't refuse")
#     print(f"Found {len(search_results)} results containing 'offer he can't refuse'")
#     for i, result in enumerate(search_results, 1):
#         print(f"\nResult #{i} from {result['movie_title']}:")
#         print(f"Matching dialogue: {result['matching_dialogue']['speaker']}: "
#               f"{result['matching_dialogue']['dialogue']}")
#         print("\nContext:")
#         for d in result["context"]:
#             prefix = ">> " if d.get("is_target") else "   "
#             print(f"{prefix}{d['speaker']}: {d['dialogue'][:60]}...")