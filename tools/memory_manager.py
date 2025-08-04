
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from config.settings import config

class MemoryManager:
    def __init__(self):
        """Initializes the MemoryManager with a persistent ChromaDB client."""
        self.client = chromadb.PersistentClient(path=config.MEMORY_DB_PATH)
        self.collection = self.client.get_or_create_collection("agent_memory")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)

    def remember(self, fact: str) -> Dict[str, Any]:
        """Saves a fact to the memory after converting it to an embedding."""
        try:
            embedding = self.model.encode(fact).tolist()
            # Use a hash of the fact as a unique identifier\
            doc_id = str(hash(fact))
            self.collection.add(embeddings=[embedding], documents=[fact], ids=[doc_id])
            return {"status": "success", "message": f"Remembered: {fact}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def recall(self, query: str, top_n: int = 3) -> List[str]:
        """remembers the most relevant memories based on a query."""
        try:
            if self.collection.count() == 0:
                return []

            query_embedding = self.model.encode(query).tolist()
            results = self.collection.query(query_embeddings=[query_embedding], n_results=top_n)
            return results["documents"][0]
        except Exception as e:
            "Return an empty string, This ensures that th model does not crash(Do not undestand why this happens yet..)"
            print(f"Error recalling memories: {e}")
            return []
