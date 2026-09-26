"""
Placeholder VisionModelClient for when no vision model is configured.

Owned by: Developer 4 (Multimodal Engineer)

Makes the absence of a model explicit: a vision request returns a FAILED
result with a clear reason, instead of crashing or, worse, returning an empty
result that could be mistaken for "nothing wrong with this equipment".

Replaced by a Model Registry adapter once Developer 2's interface is fixed.
"""

from typing import Optional

from workbench.multimodal.errors import VisionModelUnavailableError
from workbench.multimodal.ports.vision_model import VisionModelResponse


class UnavailableVisionClient:
    def __init__(self, reason: str = "No vision model configured") -> None:
        self._reason = reason

    @property
    def name(self) -> str:
        return "unavailable"

    def generate(
        self,
        image_png: bytes,
        prompt: str,
        max_output_tokens: Optional[int] = None,
    ) -> VisionModelResponse:
        raise VisionModelUnavailableError(self._reason)
