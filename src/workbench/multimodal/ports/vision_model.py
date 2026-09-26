"""
Port: a vision-language model this subsystem can ask about an image.

Owned by: Developer 4 (Multimodal Engineer)

WHY A PORT OF OUR OWN: model selection belongs to the Model Registry
(Developer 2, src/workbench/models/). This subsystem must not know which
model runs, where, or how it is served. It needs only "send an image and an
instruction, get text back". An adapter over the registry implements this
port once the registry interface is fixed; until then tests use a fake.

The port returns RAW TEXT, deliberately. Parsing and validating the model's
output is our job, because model output is untrusted input: it may be
malformed, wrapped in prose, missing fields, or steered by instructions
written inside the image itself.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class VisionModelResponse:
    text: str
    model_name: str
    box_scale: float = 1.0
    """What the model's box coordinates are measured against.

    Model families differ: some return boxes normalised to 0-1, others to
    0-1000. The adapter declares its model's convention here and the
    pipeline converts to our canonical 0-1 space. Never assume.
    """


@runtime_checkable
class VisionModelClient(Protocol):
    @property
    def name(self) -> str:
        """Stable identity recorded in evidence, e.g. 'qwen2.5-vl-7b'."""
        ...

    def generate(
        self,
        image_png: bytes,
        prompt: str,
        max_output_tokens: Optional[int] = None,
    ) -> VisionModelResponse:
        """Ask the model about one image.

        Raises VisionModelUnavailableError if no model can be reached.
        """
        ...
