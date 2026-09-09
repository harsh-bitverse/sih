"""
Tool Registry Interface.

Owned by: Developer 5 (Tool/Sandbox Engineer)
Subsystem: tools

Placeholder capabilities:
- read_file
- write_file
- python_execute
- document_generation
- spreadsheet_generation
"""

from typing import List


class ToolRegistry:
    """
    Registry maintaining safe local tool capabilities available to agents.
    """

    SUPPORTED_INITIAL_TOOLS = [
        "read_file",
        "write_file",
        "python_execute",
        "document_generation",
        "spreadsheet_generation",
    ]

    def list_available_tools(self) -> List[str]:
        """
        Returns list of registered tool names.
        """
        return list(self.SUPPORTED_INITIAL_TOOLS)
