"""RAG Answer Service connecting context retrieval to model generation."""

from typing import Any, Dict, List, Optional

from backend.app.models.base import BaseModel
from backend.app.models.local_llm import LocalLLM
from backend.app.rag.rag_service import RAGService


class RAGAnswerService:
    """End-to-end RAG answer service that retrieves context and generates answers.

    Combines semantic search from RAGService with local inference from LocalLLM (or any BaseModel)
    to produce grounded answers based strictly on stored knowledge.
    """

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        model: Optional[BaseModel] = None,
    ) -> None:
        """Initialize the RAGAnswerService.

        Args:
            rag_service: Optional RAGService instance. Defaults to a new RAGService().
            model: Optional BaseModel instance. Defaults to LocalLLM(model_name="llama3.2:latest").
        """
        self.rag_service = rag_service if rag_service is not None else RAGService()
        self.model = (
            model
            if model is not None
            else LocalLLM(model_name="llama3.2:latest")
        )

    def answer(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """Retrieve relevant context chunks and generate a grounded answer to the query.

        Args:
            query: The user's question or search query.
            n_results: Maximum number of relevant document chunks to retrieve (defaults to 3).

        Returns:
            Dictionary containing:
            - 'query': The original user question.
            - 'answer': The generated answer string from the model.
            - 'sources': List of chunk IDs used as context for the answer.
        """
        # Step 1: Retrieve matching chunks from vector store
        search_result = self.rag_service.search(query=query, n_results=n_results)

        # Step 2: Extract retrieved document texts and source IDs
        raw_documents = search_result.get("documents", [])
        raw_ids = search_result.get("ids", [])

        # Chroma query returns lists wrapped in a batch list: [[doc1, doc2, ...]]
        documents: List[str] = (
            raw_documents[0]
            if raw_documents and isinstance(raw_documents[0], list)
            else raw_documents
        )
        sources: List[str] = (
            raw_ids[0] if raw_ids and isinstance(raw_ids[0], list) else raw_ids
        )

        # Step 3: Format the context text
        if documents:
            context_text = "\n\n".join(documents)
        else:
            context_text = "No relevant context available."

        # Step 4: Construct the structured prompt
        prompt = (
            "Answer the question using ONLY the provided context.\n"
            "If the context does not contain enough information, say that\n"
            "the information is not available in the provided documents.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question:\n{query}"
        )

        # Step 5: Generate answer using the configured model
        answer_text = self.model.generate(prompt)

        # Step 6: Return structured response dictionary
        return {
            "query": query,
            "answer": answer_text,
            "sources": sources,
        }
