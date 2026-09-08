from langchain_core.tools import tool
import os
import subprocess
import requests
from app.core.rbac import RBACManager
from app.core.audit import AuditLogger

def map_role_to_manoj(role: str) -> str:
    mapping = {
        "Site Operator": "web_dev",
        "Engineer": "department_lead",
        "Department Manager": "department_lead",
        "Procurement": "management",
        "Plant Head": "vp_ceo",
        "Executive": "vp_ceo"
    }
    return mapping.get(role, "web_dev")

@tool
def search_kb(query: str, user_id: str = "agent", role: str = "web_dev") -> str:
    """Search the knowledge base for instructions, vendor data, or docs."""
    manoj_role = map_role_to_manoj(role)
    try:
        response = requests.post(
            "http://127.0.0.1:8001/kb/search",
            json={"query": query, "user": user_id, "role": manoj_role},
            timeout=15
        )
        response.raise_for_status()
        res_data = response.json()
        if res_data.get("denied"):
            return f"Access Denied by Knowledge Base: {res_data.get('denial_reason')}"
        
        chunks = res_data.get("chunks", [])
        if not chunks:
            return f"No results found in KB for '{query}'"
            
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(f"[Source {i}: {c.get('filename')} (access={c.get('access_level')})]\n{c.get('text')}")
        return "\n\n---\n\n".join(parts)
    except requests.Timeout:
        return "Error: Knowledge base unavailable (timeout)."
    except Exception as e:
        return f"Error querying knowledge base: {e}"

@tool
def generate_docx(
    template: str = "approval_note", 
    title: str = "Plant Equipment Inspection & Compliance Approval Note", 
    summary: str = "PLACEHOLDER — NOT GROUNDED: Summary not provided by agent.",
    findings: str = "PLACEHOLDER — NOT GROUNDED: No telemetry findings provided.",
    recommendation: str = "PLACEHOLDER — NOT GROUNDED: Recommendation not provided by agent.",
    sources: str = ""
) -> str:
    """Generate an enterprise DOCX approval note or detailed technical report."""
    try:
        findings_list = [f.strip("- *") for f in findings.splitlines() if f.strip()]
        if not findings_list:
            findings_list = ["PLACEHOLDER — NOT GROUNDED: No telemetry findings extracted."]
            
        sources_list = [s.strip("- *") for s in sources.splitlines() if s.strip()]
        if not sources_list:
            sources_list = [
                "Field Inspection Deliverable / Uploaded Scan",
                "Plant Operating Standard & Tolerance Guidelines",
                "CMMS Asset Verification Record"
            ]

        content = {
            "title": title,
            "summary": summary,
            "findings": findings_list,
            "sources": sources_list,
            "recommendation": recommendation,
            "sections": [
                {
                    "heading": "1. Technical Inspection Findings",
                    "body": findings_list
                },
                {
                    "heading": "2. Standards & Operational Grounding",
                    "body": f"Documented findings evaluated against operating standards. Summary: {summary}"
                },
                {
                    "heading": "3. Risk Assessment & Disposition",
                    "body": f"Operational evaluation: {recommendation}"
                }
            ],
            "conclusion": f"Evaluation concluded. Recommendation: {recommendation}"
        }
        response = requests.post(
            "http://127.0.0.1:8001/generate/docx",
            json={"template": template, "content": content},
            timeout=15
        )
        response.raise_for_status()
        filename = response.json().get('filename')
        return f"Successfully generated DOCX: {filename} with findings: {findings_list}"
    except requests.Timeout:
        return "Error: Document generator unavailable (timeout)."
    except Exception as e:
        return f"Error generating DOCX: {e}"

@tool
def generate_pptx(template: str, title: str, findings: str) -> str:
    """Generate a PPTX presentation deck."""
    try:
        response = requests.post(
            "http://127.0.0.1:8001/generate/pptx",
            json={"template": template, "content": {"title": title, "findings": [{"heading": "Finding", "body": findings}]}},
            timeout=15
        )
        response.raise_for_status()
        return f"Successfully generated PPTX: {response.json().get('filename')}"
    except requests.Timeout:
        return "Error: Document generator unavailable (timeout)."
    except Exception as e:
        return f"Error generating PPTX: {e}"

@tool
def generate_xlsx(template: str, title: str, data: str) -> str:
    """Generate an XLSX data table."""
    try:
        response = requests.post(
            "http://127.0.0.1:8001/generate/xlsx",
            json={"template": template, "content": {"title": title, "headers": ["Data"], "rows": [[data]]}},
            timeout=15
        )
        response.raise_for_status()
        return f"Successfully generated XLSX: {response.json().get('filename')}"
    except requests.Timeout:
        return "Error: Document generator unavailable (timeout)."
    except Exception as e:
        return f"Error generating XLSX: {e}"

@tool
def write_file(filename: str, content: str) -> str:
    """Write content to a file on disk."""
    path = os.path.join(os.getcwd(), filename)
    try:
        with open(path, "w") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} chars to {filename}"
    except Exception as e:
        return f"Failed to write file {filename}: {e}"

@tool
def read_file(filename: str) -> str:
    """Read content from a file on disk."""
    path = os.path.join(os.getcwd(), filename)
    try:
        if not os.path.exists(path):
            return f"Error: File '{filename}' does not exist."
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Failed to read file {filename}: {e}"

@tool
def run_python_code(code: str) -> str:
    """Executes python code in a secure sandbox."""
    try:
        response = requests.post(
            "http://127.0.0.1:8001/tools/run_code",
            json={"code": code, "timeout": 5, "stdin": ""},
            timeout=10
        )
        response.raise_for_status()
        res = response.json()
        
        output = res.get("stdout", "")
        if res.get("stderr"):
            output += f"\nErrors:\n{res.get('stderr')}"
            
        if res.get("timed_out"):
            return "Error: Code execution timed out."
            
        return f"Execution successful:\n{output}" if res.get("exit_code") == 0 else f"Execution failed:\n{output}"
    except requests.Timeout:
        return "Error: Sandbox microservice unavailable (timeout)."
    except Exception as e:
        return f"Error executing sandbox microservice: {e}"

class ToolRegistry:
    """
    Central registry for all local tools (sandbox, KB search, doc-gen).
    Every tool call passes through the RBAC gate first.
    """
    
    def __init__(self):
        self.tools = {}
        self.rbac = RBACManager()
        self.audit = AuditLogger()
        
        # Automatically register default tools
        self.register_tool("search_kb", search_kb)
        self.register_tool("generate_docx", generate_docx)
        self.register_tool("generate_pptx", generate_pptx)
        self.register_tool("generate_xlsx", generate_xlsx)
        self.register_tool("write_file", write_file)
        self.register_tool("read_file", read_file)
        self.register_tool("run_python_code", run_python_code)
        
    def register_tool(self, name: str, func):
        self.tools[name] = func
        
    def execute_tool(self, name: str, user_role: str, **kwargs):
        """
        Executes a tool after performing Role-Based Access Control (RBAC) checks.
        """
        if name not in self.tools:
            self.audit.log_action("TOOL_ATTEMPT", user_role, name, kwargs, "TOOL_NOT_FOUND")
            return f"Error: Tool '{name}' not found."
            
        # The RBAC gate is enforced here before the tool is even invoked
        # This prevents the LLM from bypassing security via prompts
        if not self.rbac.can_execute(user_role, name, **kwargs):
            self.audit.log_action("RBAC_EVALUATION", user_role, name, kwargs, "DENIED")
            return f"Access Denied: Security policy blocked role '{user_role}' from executing '{name}' with these parameters."
            
        self.audit.log_action("RBAC_EVALUATION", user_role, name, kwargs, "GRANTED")
        
        try:
            tool = self.tools[name]
            clean_kwargs = {k: v for k, v in kwargs.items() if k not in ["task_context", "user_id", "role"]}
            if hasattr(tool, "invoke"):
                result = tool.invoke(clean_kwargs)
            else:
                result = tool(**clean_kwargs)
            self.audit.log_action("TOOL_EXECUTION", user_role, name, kwargs, "SUCCESS")
            return result
        except Exception as e:
            self.audit.log_action("TOOL_EXECUTION", user_role, name, kwargs, f"FAILED: {str(e)}")
            return f"Error executing tool {name}: {str(e)}"
