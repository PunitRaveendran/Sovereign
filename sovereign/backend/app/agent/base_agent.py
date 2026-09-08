"""Agent with planning, tool use, answer generation, and critique."""

from typing import Any, Dict, List

from backend.app.models.base import BaseModel
from backend.app.agent.tools import RAGSearchTool
from backend.app.agent.answer_generator import AnswerGenerator


class Agent:
    """Sovereign agent that can plan, use tools, and generate answers."""

    def __init__(self, model: BaseModel) -> None:
        """Initialize the agent."""
        self.model = model
        self.rag_tool = RAGSearchTool()
        self.answer_generator = AnswerGenerator(model)

    def plan(self, task: str) -> str:
        """Create a plan for the task."""

        prompt = (
            "You are an AI planning agent.\n"
            "Create a clear, concise step-by-step plan "
            "to accomplish the following task.\n\n"
            f"Task: {task}\n\n"
            "Plan:"
        )

        return self.model.generate(prompt)

    def act(self, task: str, plan: str) -> Dict[str, Any]:
        """Execute the plan using the RAG tool."""

        rag_result = self.rag_tool.run(
            query=task,
            n_results=3,
        )

        return {
            "tool": self.rag_tool.name,
            "tool_input": task,
            "tool_result": rag_result,
            "plan": plan,
        }

    def generate_answer(
        self,
        task: str,
        execution: Dict[str, Any],
    ) -> str:
        """Generate a final answer from retrieved documents."""

        raw_documents = execution["tool_result"].get(
            "documents",
            [],
        )

        if raw_documents and isinstance(raw_documents[0], list):
            documents: List[str] = raw_documents[0]
        else:
            documents = raw_documents

        return self.answer_generator.generate(
            question=task,
            documents=documents,
        )

    def observe(
        self,
        result: Dict[str, Any],
    ) -> str:
        """Observe the tool execution result."""

        prompt = (
            "You are an AI observer.\n"
            "Inspect the following tool execution result "
            "and describe what was found.\n\n"
            f"Tool execution result:\n{result}\n\n"
            "Observations:"
        )

        return self.model.generate(prompt)

    def critique(
        self,
        task: str,
        result: Dict[str, Any],
    ) -> str:
        """Evaluate whether the result satisfies the task."""

        prompt = (
            "You are an AI critique agent.\n"
            "Evaluate whether the following result accurately "
            "and completely satisfies the original task.\n\n"
            f"Original Task: {task}\n\n"
            f"Execution Result:\n{result}\n\n"
            "Critique:"
        )

        return self.model.generate(prompt)

    def run(self, task: str) -> Dict[str, Any]:
        """Run the complete agent workflow."""

        # 1. Create a plan
        plan_output = self.plan(task)

        # 2. Execute the plan using a real tool
        execution_output = self.act(
            task=task,
            plan=plan_output,
        )

        # 3. Generate the final answer from retrieved documents
        answer_output = self.generate_answer(
            task=task,
            execution=execution_output,
        )

        # 4. Observe the execution
        observation_output = self.observe(
            execution_output
        )

        # 5. Critique the result
        critique_output = self.critique(
            task=task,
            result=execution_output,
        )

        return {
            "task": task,
            "plan": plan_output,
            "execution": execution_output,
            "answer": answer_output,
            "observation": observation_output,
            "critique": critique_output,
        }