import chromadb
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Any
from datetime import datetime
from config.settings import config
import hashlib

class MemoryManager:
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initializes the MemoryManager with a persistent ChromaDB client.
        Includes semantic deduplication and smart memory handling.
        """
        self.client = chromadb.PersistentClient(path=config.MEMORY_DB_PATH)
        self.collection = self.client.get_or_create_collection("agent_memory")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.similarity_threshold = similarity_threshold

    def _generate_id(self, fact: str) -> str:
        """Generates a consistent unique ID using SHA256."""
        return hashlib.sha256(fact.encode('utf-8')).hexdigest()

    def _is_duplicate(self, fact: str, top_k: int = 5) -> bool:
        """Checks if a semantically similar memory already exists."""
        if self.collection.count() == 0:
            return False

        embedding = self.model.encode(fact)
        results = self.collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=top_k
        )

        for existing_fact in results.get("documents", [[]])[0]:
            existing_embedding = self.model.encode(existing_fact)
            similarity = util.cos_sim(embedding, existing_embedding).item()
            if similarity >= self.similarity_threshold:
                return True
        return False

    def remember(self, fact: str) -> Dict[str, Any]:
        """Saves a fact to memory after checking for duplication."""
        try:
            if self._is_duplicate(fact):
                return {"status": "skipped", "message": "Fact already exists (semantically similar)."}

            embedding = self.model.encode(fact).tolist()
            doc_id = self._generate_id(fact)
            metadata = {"timestamp": datetime.utcnow().isoformat()}

            self.collection.add(
                embeddings=[embedding],
                documents=[fact],
                ids=[doc_id],
                metadatas=[metadata]
            )
            return {"status": "success", "message": f"Remembered: {fact}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def recall(self, query: str, top_n: int = 3) -> List[str]:
        """Returns the most relevant memories based on a query."""
        try:
            if self.collection.count() == 0:
                return []

            query_embedding = self.model.encode(query).tolist()
            results = self.collection.query(query_embeddings=[query_embedding], n_results=top_n)
            return results.get("documents", [[]])[0]
        except Exception as e:
            print(f"[MemoryManager] Error recalling memories: {e}")
            return []
    def forget(self, fact: str, confirm: bool = False, similarity_threshold: float = 0.85, top_n: int = 3) -> Dict[str, Any]:
        """
        Searches for and (optionally) removes semantically similar facts from memory.

        Parameters:
        - fact (str): The fact to forget.
        - confirm (bool): If True, deletes the matched memory. Otherwise, just returns candidates.
        - similarity_threshold (float): Cosine similarity threshold to consider a match.
        - top_n (int): Number of top candidates to search.

        Returns:
        - Dict with status and optionally deleted or matched memories.
        """
        try:
            if self.collection.count() == 0:
                return {"status": "empty", "message": "No memories to search."}

            query_embedding = self.model.encode(fact)
            results = self.collection.query(query_embeddings=[query_embedding.tolist()], n_results=top_n)
            candidates = results.get("documents", [[]])[0]
            ids = results.get("ids", [[]])[0]

            deleted = []
            matched = []

            for doc, doc_id in zip(candidates, ids):
                doc_embedding = self.model.encode(doc)
                similarity = util.cos_sim(query_embedding, doc_embedding).item()

                if similarity >= similarity_threshold:
                    matched.append({"fact": doc, "similarity": round(similarity, 3), "id": doc_id})
                    if confirm:
                        self.collection.delete(ids=[doc_id])
                        deleted.append(doc)

            if not matched:
                return {"status": "not_found", "message": "No similar memory found to forget."}

            if confirm:
                return {
                    "status": "success",
                    "message": f"Deleted {len(deleted)} similar memory item(s).",
                    "deleted_facts": deleted
                }
            else:
                return {
                    "status": "match_found",
                    "message": f"{len(matched)} similar memory item(s) found.",
                    "matches": matched
                }

        except Exception as e:
            return {"status": "error", "message": f"Failed during semantic forget: {str(e)}"}
