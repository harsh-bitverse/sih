"""
OCR Engine Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from workbench.core.types import Evidence, ResourceReference


class OCREngine:
    """
    Interface for optical character recognition engines.
    """

    def extract_text(self, resource: ResourceReference) -> list[Evidence]:
        """
        Extracts text bounding boxes and line evidence from document images.
        """
        raise NotImplementedError("OCREngine.extract_text will be implemented by Developer 4.")
