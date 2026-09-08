class RBACManager:
    """
    Role-Based Access Control matrix for the Sovereign AI Workbench.
    Implements domain-aware compartmentalized access (PSU/Refinery realistic).
    """
    
    # Roles
    ROLES = [
        "Site Operator",
        "Engineer",
        "Department Manager",
        "Procurement",
        "Plant Head",
        "Executive"
    ]
    
    # Base Tool Access (Vertical Hierarchy)
    ROLE_TOOL_ACCESS = {
        "Site Operator": ["search_kb", "read_file", "generate_docx", "generate_pptx", "generate_xlsx"],
        "Engineer": ["search_kb", "read_file", "run_python_code", "write_file", "generate_docx", "generate_pptx", "generate_xlsx"],
        "Department Manager": ["search_kb", "read_file", "run_python_code", "write_file", "generate_docx", "generate_pptx", "generate_xlsx"],
        "Procurement": ["search_kb", "read_file", "write_file", "generate_docx", "generate_pptx", "generate_xlsx"],
        "Plant Head": ["search_kb", "read_file", "run_python_code", "write_file", "generate_docx", "generate_pptx", "generate_xlsx"],
        "Executive": ["search_kb", "read_file", "run_python_code", "write_file", "generate_docx", "generate_pptx", "generate_xlsx"]
    }
    
    # Compartmentalized Data Access (Lateral Hierarchy)
    # Enforces Row-Level Security by inspecting query/filename kwargs
    RESTRICTED_KEYWORDS = {
        "financial": ["Department Manager", "Plant Head", "Executive"],
        "vendor": ["Procurement", "Plant Head", "Executive"],
        "pricing": ["Procurement", "Plant Head", "Executive"],
        "unreleased": ["Plant Head", "Executive"],
        "board": ["Executive"]
    }

    def can_execute(self, role: str, tool_name: str, **kwargs) -> bool:
        """
        Returns True if the role is allowed to execute the tool with the given arguments.
        """
        # 1. Verify role exists
        if role not in self.ROLE_TOOL_ACCESS:
            return False
            
        # 2. Check Global Tool Access 
        allowed_tools = self.ROLE_TOOL_ACCESS[role]
        if tool_name not in allowed_tools:
            return False
            
        # 3. Check Compartmentalized Data Access
        # For the hackathon MVP, we inspect the tool arguments for sensitive keywords
        args_str = str(kwargs).lower()
        for keyword, allowed_roles in self.RESTRICTED_KEYWORDS.items():
            if keyword in args_str:
                if role not in allowed_roles:
                    return False
                    
        return True
