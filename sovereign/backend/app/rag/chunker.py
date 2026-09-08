"""Document chunking module for Sovereign RAG pipeline."""

from typing import List


class DocumentChunker:
    """Splits long text documents into smaller, overlapping text chunks.

    Chunking allows large documents to fit within the embedding model's context
    window while maintaining contextual continuity across chunk boundaries via overlap.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        """Initialize the DocumentChunker with size and overlap parameters.

        Args:
            chunk_size: Maximum number of characters allowed in each chunk. Defaults to 500.
            chunk_overlap: Approximate number of overlapping characters between consecutive chunks.
                           Defaults to 50.

        Raises:
            ValueError: If chunk_size <= 0, chunk_overlap < 0, or chunk_overlap >= chunk_size.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """Split input text into overlapping chunks of at most chunk_size characters.

        Args:
            text: The raw document text string to chunk.

        Returns:
            A list of non-empty text chunk strings. Returns an empty list if input
            is empty or contains only whitespace.
        """
        # Handle empty, None, or whitespace-only inputs
        if not text or not isinstance(text, str) or not text.strip():
            return []

        cleaned_text = text.strip()
        text_length = len(cleaned_text)

        # If the text is already shorter than or equal to chunk_size, return it directly
        if text_length <= self.chunk_size:
            return [cleaned_text]

        chunks: List[str] = []
        start_index = 0
        step_size = self.chunk_size - self.chunk_overlap

        # Slide window across the text
        while start_index < text_length:
            end_index = start_index + self.chunk_size
            chunk = cleaned_text[start_index:end_index]

            # Only append non-empty chunks
            if chunk.strip():
                chunks.append(chunk)

            # If this chunk reaches the end of the text, stop sliding
            if end_index >= text_length:
                break

            start_index += step_size

        return chunks
