"""Local embedding function implementation for Sovereign RAG pipeline."""

from typing import List, Optional, Union

from sentence_transformers import SentenceTransformer

try:
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
except ImportError:
    try:
        from chromadb import Documents, EmbeddingFunction, Embeddings  # type: ignore
    except ImportError:
        Documents = List[str]  # type: ignore
        Embeddings = List[List[float]]  # type: ignore

        class EmbeddingFunction:  # type: ignore
            """Fallback base class if ChromaDB is not installed."""
            pass

# Default offline embedding model
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class LocalEmbeddingFunction(EmbeddingFunction[Documents]):
    """Local SentenceTransformer embedding function compatible with ChromaDB.

    The model may need to be downloaded once during initial setup. Once the model
    is available locally (or pre-cached), all vector embeddings are generated
    entirely on-premise without making cloud API calls.
    """
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        device: Optional[str] = None,
    ) -> None:
        """Initialize the local embedding model.

        Args:
            model_name: HuggingFace model identifier or local path.
                        Defaults to 'BAAI/bge-small-en-v1.5'.
            device: Execution device (e.g. 'cpu', 'cuda'). Defaults to automatic detection.
        """
        self.model_name = model_name
        self.device = device
        self.model = SentenceTransformer(self.model_name, device=self.device)

    def __call__(self, input: Documents) -> Embeddings:
        """Generate vector embeddings for a list of text documents.

        Args:
            input: A list of text strings (or a single text string) to embed.

        Returns:
            A list of float lists representing dense vector embeddings.
        """
        if isinstance(input, str):
            input = [input]

        # Generate embeddings locally using the SentenceTransformer model
        raw_embeddings = self.model.encode(
            input,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return raw_embeddings.tolist()

    def name(self) -> str:
        """Return a descriptive name identifier for the embedding function.

        Returns:
            String identifier for ChromaDB embedding registry.
        """
        return f"local_{self.model_name.replace('/', '_')}"
