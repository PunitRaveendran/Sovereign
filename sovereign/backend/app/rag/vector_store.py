"""Local persistent vector store module for Sovereign RAG pipeline using ChromaDB."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chromadb

from backend.app.rag.embeddings import LocalEmbeddingFunction

# Default path for persistent local vector storage
DEFAULT_PERSIST_DIRECTORY = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "chroma"
)
DEFAULT_COLLECTION_NAME = "sovereign_knowledge"


class VectorStore:
    """Local persistent vector store managing document embeddings and semantic search.

    Operates completely offline using ChromaDB's persistent local client stored on disk
    at data/chroma with zero cloud API dependencies.
    """

    def __init__(
        self,
        persist_directory: Optional[Union[str, Path]] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_function: Optional[Any] = None,
    ) -> None:
        """Initialize the VectorStore with a local persistent ChromaDB client.

        Args:
            persist_directory: Optional directory path for disk persistence.
                               Defaults to 'data/chroma' in the project root.
            collection_name: Name of the Chroma collection. Defaults to 'sovereign_knowledge'.
            embedding_function: Optional custom embedding function. If omitted,
                                defaults to LocalEmbeddingFunction using BAAI/bge-small-en-v1.5.
        """
        self.persist_directory = (
            Path(persist_directory) if persist_directory else DEFAULT_PERSIST_DIRECTORY
        )
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_function = (
            embedding_function if embedding_function is not None else LocalEmbeddingFunction()
        )

        # Initialize local persistent Chroma client
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))

        # Create or get existing collection configured with local embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
        )

    def add_documents(self, documents: List[str], ids: List[str]) -> None:
        """Add text documents and their corresponding unique identifiers to the collection.

        Args:
            documents: List of text strings to store and embed.
            ids: List of unique string identifiers corresponding to each document.
        """
        if not documents or not ids:
            return

        self.collection.add(
            documents=documents,
            ids=ids,
        )

    def count(self) -> int:
        """Return the total number of documents currently stored in the collection.

        Returns:
            An integer representing the document count.
        """
        return self.collection.count()

    def search(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """Perform a semantic similarity search across stored documents.

        Args:
            query: The search query text prompt.
            n_results: Maximum number of nearest document matches to return (defaults to 3).

        Returns:
            Dictionary containing search results with matched documents, IDs, and distances.
        """
        total_docs = self.count()
        if total_docs == 0:
            return {"ids": [[]], "documents": [[]], "distances": [[]], "metadatas": [[]]}

        effective_n = min(n_results, total_docs)
        return self.collection.query(
            query_texts=[query],
            n_results=effective_n,
        )
