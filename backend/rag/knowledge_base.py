"""
RAG Knowledge Base
ChromaDB-backed vector store for agricultural knowledge retrieval.
Uses Chroma's DefaultEmbeddingFunction.
"""

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.utils import embedding_functions
from config import settings


class AgriKnowledgeBase:
    """Agricultural knowledge base with semantic search."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        
        # Use Ollama for embeddings to avoid downloading default models
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="agri_knowledge",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = False

    def is_populated(self) -> bool:
        """Check if the knowledge base has documents."""
        return self.collection.count() > 0

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """Add documents to the knowledge base."""
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def query(self, question: str, n_results: int = 3) -> str:
        """
        Query the knowledge base and return relevant context.
        Uses ChromaDB's built-in embedding (default model).
        """
        if self.collection.count() == 0:
            return ""

        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=min(n_results, self.collection.count()),
            )

            if not results or not results.get("documents"):
                return ""

            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]

            context_parts = []
            for i, doc in enumerate(docs):
                source = metas[i].get("source", "knowledge-base") if i < len(metas) else "knowledge-base"
                context_parts.append(f"[Source: {source}]\n{doc}")

            return "\n\n---\n\n".join(context_parts)

        except Exception as e:
            print(f"[RAG] Query error: {e}")
            return ""

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        return {
            "total_documents": self.collection.count(),
            "collection_name": "agri_knowledge",
        }


# Global instance
knowledge_base = AgriKnowledgeBase()
