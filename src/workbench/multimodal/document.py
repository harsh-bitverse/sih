"""
Document Parser Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference
from workbench.multimodal.processor import MultimodalProcessor
from workbench.multimodal.schemas import MultimodalRequest, MultimodalResult


class DocumentParser:
    """
    Interface for structured layout and document parsing.
    """

    def parse_document(self, resource: ResourceReference) -> MultimodalResult:
        """
        Parses multi-page PDF/Word/Technical documents into structured sections and evidence.
        """
        raise NotImplementedError("DocumentParser.parse_document will be implemented by Developer 4.")


class OcrDocumentParser(DocumentParser):
    """Slice 1: parses via OCR only. Layout segmentation lands in slice 3.

    parse_document has no RequestContext in its signature, so one is supplied
    at construction. Callers that already hold a context should prefer
    MultimodalProcessor.process, which propagates the caller's own.
    """

    def __init__(self, processor: MultimodalProcessor, context: RequestContext) -> None:
        self._processor = processor
        self._context = context

    def parse_document(self, resource: ResourceReference) -> MultimodalResult:
        return self._processor.process(
            MultimodalRequest(
                request_context=self._context,
                resource=resource,
                modalities=["ocr"],
            )
        )
