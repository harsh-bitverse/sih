"""
Multimodal Processor Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from workbench.multimodal.schemas import MultimodalRequest, MultimodalResult


class MultimodalProcessor:
    """
    Main entrypoint interface for multimodal processing requests.
    """

    def process(self, request: MultimodalRequest) -> MultimodalResult:
        """
        Processes document/image/audio input and returns structured MultimodalResult.
        """
        raise NotImplementedError("MultimodalProcessor.process will be implemented by Developer 4.")
