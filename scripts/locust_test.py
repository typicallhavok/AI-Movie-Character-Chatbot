from locust import HttpUser, task, between
import random

class MovieCharacterUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.user_id = f"test_user_{random.randint(1000, 9999)}"
    
    @task(3)
    def search_dialogue(self):
        movie_lines = [
            "I'll be back",
            "May the force be with you",
            "Here's looking at you, kid",
            "Show me the money",
            "You talking to me?"
        ]
        
        query = random.choice(movie_lines)
        self.client.post(
            "/search_dialogue", 
            json={"search_query": query, "top_k": 3},
            name="/search_dialogue"
        )
    
    @task(1)
    def get_user_chats(self):
        self.client.get(f"/get_user_chats?user_id={self.user_id}", name="/get_user_chats")
    
    @task(1)
    def health_check(self):
        self.client.get("/", name="Health Check")

    @task(2)
    def simulate_chat_sequence(self):
        sample_queries = [
            "What's your favorite part of the movie?",
            "Tell me about your character",
            "How would you react to danger?",
            "What motivates you in this scene?"
        ]
        
        for _ in range(3):
            query = random.choice(sample_queries)
            self.client.post(
                "/search_dialogue", 
                json={"search_query": query, "top_k": 1},
                name="Simulated Chat Message"
            )