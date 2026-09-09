"""
Multimodal Subsystem Package.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from workbench.multimodal.schemas import (
    MultimodalStatus,
    MultimodalRequest,
    MultimodalResult,
    Modality,
    SUPPORTED_MODALITIES,
)
from workbench.multimodal.processor import MultimodalProcessor, DefaultMultimodalProcessor
from workbench.multimodal.ocr import OCREngine, TesseractOCREngine
from workbench.multimodal.vision import VisionEngine
from workbench.multimodal.document import DocumentParser, OcrDocumentParser
from workbench.multimodal.errors import (
    MultimodalError,
    DocumentUnreadableError,
    DocumentEncryptedError,
    OcrBackendUnavailableError,
    ArtifactStoreError,
    ResourceResolutionError,
    ResourceAccessDeniedError,
)

__all__ = [
    "MultimodalStatus",
    "MultimodalRequest",
    "MultimodalResult",
    "Modality",
    "SUPPORTED_MODALITIES",
    "MultimodalProcessor",
    "DefaultMultimodalProcessor",
    "OCREngine",
    "TesseractOCREngine",
    "VisionEngine",
    "DocumentParser",
    "OcrDocumentParser",
    "MultimodalError",
    "DocumentUnreadableError",
    "DocumentEncryptedError",
    "OcrBackendUnavailableError",
    "ArtifactStoreError",
    "ResourceResolutionError",
    "ResourceAccessDeniedError",
]
