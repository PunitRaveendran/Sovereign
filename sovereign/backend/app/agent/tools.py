"""Tools available to the Sovereign agent."""

from typing import Any, Dict, Optional

from backend.app.rag.rag_service import RAGService


class RAGSearchTool:
    """Tool that searches the local Sovereign knowledge base."""

    name = "rag_search"
    description = (
        "Search the local Sovereign knowledge base "
        "for relevant document chunks."
    )

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
    ) -> None:
        """Initialize the RAG search tool."""

        self.rag_service = (
            rag_service
            if rag_service is not None
            else RAGService()
        )

    def run(
        self,
        query: str,
        n_results: int = 3,
    ) -> Dict[str, Any]:
        """Search the local knowledge base."""

        return self.rag_service.search(
            query=query,
            n_results=n_results,
        )