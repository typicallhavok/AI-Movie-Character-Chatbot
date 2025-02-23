import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm
import concurrent.futures
import time

load_dotenv()

# Initialize MongoDB
mongo_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = mongo_client.movie_database
dialogues_collection = db.dialogues

# Extract dialogues from JSON
def extract_dialogues_from_json(json_data):
    movie_title = json_data.get("movie_title", "Unknown Movie")
    content = json_data.get("content", "")

    dialogues = []
    current_speaker = None
    current_dialogue = []

    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.isupper() and len(line.split()) <= 3:  # Character name
            if current_speaker and current_dialogue:
                dialogues.append((current_speaker, " ".join(current_dialogue)))
            current_speaker = line
            current_dialogue = []
        elif current_speaker:
            current_dialogue.append(line)

    if current_speaker and current_dialogue:
        dialogues.append((current_speaker, " ".join(current_dialogue)))

    return movie_title, dialogues

# Process a single dialogue
def process_single_dialogue(args):
    dialogue_id, movie_title, speaker, dialogue = args
    
    try:
        # Check if the dialogue already exists in MongoDB
        existing_document = dialogues_collection.find_one({"_id": dialogue_id})

        if existing_document:
            return f"Skipped existing: {movie_title}, Speaker: {speaker}"
        else:
            # Store new document in MongoDB
            dialogues_collection.insert_one({
                "_id": dialogue_id,
                "title": movie_title,
                "speaker": speaker,
                "dialogue": dialogue,
                "created_at": time.time()
            })
            
            return f"Processed: {movie_title}, Speaker: {speaker}"
    except Exception as e:
        return f"Error processing {dialogue_id}: {str(e)}"

def process_batch(batch):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        batch_results = list(executor.map(process_single_dialogue, batch))
        results.extend(batch_results)
    return results

def store_json_dialogues_in_mongodb(folder_path, batch_size=20):
    # Create index for faster queries
    dialogues_collection.create_index("title")
    dialogues_collection.create_index("speaker")
    
    # Get all JSON files
    json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    print(f"Found {len(json_files)} JSON files")
    
    all_dialogue_tasks = []
    
    # First, extract all dialogues from all files
    for filename in tqdm(json_files, desc="Preparing files"):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                json_data = json.load(file)
                movie_title, dialogues = extract_dialogues_from_json(json_data)
                
                # Create tasks for each dialogue
                for i, (speaker, dialogue) in enumerate(dialogues):
                    dialogue_id = f"{movie_title}_{i}"
                    all_dialogue_tasks.append((dialogue_id, movie_title, speaker, dialogue))
            except json.JSONDecodeError:
                print(f"Error: Could not parse JSON in {filename}")
    
    total_dialogues = len(all_dialogue_tasks)
    print(f"Total dialogues to process: {total_dialogues}")
    
    # Process in batches
    results = []
    for i in tqdm(range(0, total_dialogues, batch_size), desc="Processing batches"):
        batch = all_dialogue_tasks[i:i+batch_size]
        batch_results = process_batch(batch)
        results.extend(batch_results)
        
        # Add a small delay between batches
        if i + batch_size < total_dialogues:
            time.sleep(0.5)
    
    # Count processed vs skipped
    processed = sum(1 for r in results if r.startswith("Processed"))
    skipped = sum(1 for r in results if r.startswith("Skipped"))
    errors = sum(1 for r in results if r.startswith("Error"))
    
    print(f"Processing complete:")
    print(f"- {processed} new dialogues processed")
    print(f"- {skipped} existing dialogues skipped")
    print(f"- {errors} errors encountered")
    
    if errors > 0:
        print("Some errors occurred during processing. Check logs for details.")

if __name__ == "__main__":
    # Run the script with batch processing
    store_json_dialogues_in_mongodb("../movie_scripts", batch_size=20)