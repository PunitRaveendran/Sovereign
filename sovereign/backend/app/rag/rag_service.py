"""RAG Service orchestrator connecting document chunking and vector storage."""

from typing import Any, Dict, Optional

from backend.app.rag.chunker import DocumentChunker
from backend.app.rag.vector_store import VectorStore


class RAGService:
    """High-level service orchestrating document ingestion, chunking, and semantic retrieval.

    Coordinates between DocumentChunker (splitting documents into smaller passages)
    and VectorStore (embedding and persisting passages for vector similarity search).
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        chunker: Optional[DocumentChunker] = None,
    ) -> None:
        """Initialize the RAGService.

        Args:
            vector_store: Optional VectorStore instance. If omitted, initializes VectorStore().
            chunker: Optional DocumentChunker instance. If omitted, initializes DocumentChunker().
        """
        self.vector_store = vector_store if vector_store is not None else VectorStore()
        self.chunker = chunker if chunker is not None else DocumentChunker()

    def add_document(self, document_id: str, text: str) -> int:
        """Chunk a text document and store all chunks with unique deterministic IDs.

        Args:
            document_id: Unique identifier for the parent document.
            text: Raw text content of the document.

        Returns:
            The number of chunks created and stored in the vector database.
        """
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            return 0

        # Construct deterministic unique ID for each chunk: {document_id}-chunk-{index}
        chunk_ids = [f"{document_id}-chunk-{i}" for i in range(len(chunks))]

        # Store chunks in the vector database
        self.vector_store.add_documents(documents=chunks, ids=chunk_ids)

        return len(chunks)

    def search(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """Perform a semantic similarity search across stored document chunks.

        Args:
            query: The user prompt or search query string.
            n_results: Maximum number of nearest matching chunks to return. Defaults to 3.

        Returns:
            Dictionary containing matched chunk documents, IDs, and similarity distances.
        """
        return self.vector_store.search(query=query, n_results=n_results)
