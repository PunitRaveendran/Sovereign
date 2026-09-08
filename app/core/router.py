import json
import re
import requests

class TaskRouter:
    """
    Classifies incoming tasks into distinct categories using local LLM inference
    to determine which model needs to be loaded into VRAM.
    """
    
    CATEGORIES = {
        "reasoning": "Reasoning / Document Work (Nemotron 9B)",
        "coding": "Coding (IBM Granite 4.1 8B)",
        "vision": "Vision / Scanned Docs (Qwen2.5-VL-7B)"
    }
    
    def __init__(self, endpoint_url: str = "http://localhost:8080/v1/chat/completions"):
        """
        Initializes the router to query the local inference engine on port 8080.
        """
        self.endpoint_url = endpoint_url
        print("TaskRouter initialized with real local neural classification.")
        
    def _build_prompt(self, task_description: str) -> str:
        prompt = f"""You are an intelligent task router for an air-gapped AI workbench.
Classify the following user task into exactly ONE of these three categories:
- "coding" (generating code, writing scripts, calculations, debug, algorithms, sandboxed execution)
- "vision" (images, scanned PDFs, blueprints, engineering drawings, OCR, handwriting)
- "reasoning" (general queries, executive reports, document summarization, policy analysis, drafting memos)

Task: "{task_description}"

Respond ONLY with a JSON object in this exact format:
{{"category": "coding"}}"""
        return prompt

    def classify(self, task_description: str) -> str:
        """
        Classifies the task description using real zero-shot local LLM inference.
        Falls back to rule-based classification if the LLM server is unreachable.
        """
        prompt = self._build_prompt(task_description)
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "You are a precise task classifier that outputs only JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 50
        }

        try:
            response = requests.post(self.endpoint_url, json=payload, timeout=60.0)
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                
                # Extract JSON block
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    cat = parsed.get("category", "").lower().strip()
                    if cat in self.CATEGORIES:
                        return self.CATEGORIES[cat]
                
                # Direct string search in LLM response if JSON parsing missed
                content_lower = content.lower()
                for cat_key in ["coding", "vision", "reasoning"]:
                    if cat_key in content_lower:
                        return self.CATEGORIES[cat_key]
        except Exception as e:
            print(f"[TaskRouter] Local LLM router query bypassed: {e}")

        # Graceful heuristic fallback if LLM is offline
        task_lower = task_description.lower()
        if any(word in task_lower for word in ["code", "script", "calculate", "function", "math", "algorithm"]):
            return self.CATEGORIES["coding"]
        elif any(word in task_lower for word in ["image", "scan", "drawing", "photo", "pdf"]):
            return self.CATEGORIES["vision"]
        else:
            return self.CATEGORIES["reasoning"]
