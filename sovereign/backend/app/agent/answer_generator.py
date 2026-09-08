"""Generate final answers from retrieved local knowledge."""

from typing import Any, Dict, List

from backend.app.models.base import BaseModel


class AnswerGenerator:
    """Generate an answer using retrieved document context."""

    def __init__(self, model: BaseModel) -> None:
        self.model = model

    def generate(
        self,
        question: str,
        documents: List[str],
    ) -> str:
        """Generate an answer using only the supplied documents."""

        if not documents:
            context = "No relevant documents were found."
        else:
            context = "\n\n".join(documents)

        prompt = (
            "You are a private enterprise AI assistant.\n"
            "Answer the user's question using ONLY the provided "
            "document context.\n"
            "Do not invent information.\n"
            "If the documents do not contain the answer, say that "
            "the information is not available in the provided "
            "documents.\n\n"
            f"Document context:\n{context}\n\n"
            f"User question:\n{question}\n\n"
            "Answer:"
        )

        return self.model.generate(prompt)