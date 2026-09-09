"""
Document Generation Tools Interface.

Owned by: Developer 5 (Tool/Sandbox Engineer)
Subsystem: tools
"""

from typing import Any, Dict
from workbench.core.artifacts import Artifact


class DocumentGenerator:
    """
    Interface for generating report documents and spreadsheet deliverables.
    """

    def generate_document(self, template_name: str, data: Dict[str, Any]) -> Artifact:
        """
        Generates a formatted document artifact.
        """
        raise NotImplementedError("DocumentGenerator.generate_document will be implemented by Developer 5.")

    def generate_spreadsheet(self, sheet_data: Dict[str, Any]) -> Artifact:
        """
        Generates a spreadsheet data artifact.
        """
        raise NotImplementedError("DocumentGenerator.generate_spreadsheet will be implemented by Developer 5.")
