"""
Vision Engine Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from workbench.core.types import Evidence, ResourceReference


class VisionEngine:
    """
    Interface for visual comprehension models.
    """

    def analyze_image(self, resource: ResourceReference, prompt: str) -> list[Evidence]:
        """
        Analyzes visual features, diagrams, and technical drawings.
        """
        raise NotImplementedError("VisionEngine.analyze_image will be implemented by Developer 4.")

# SLICE 2 (blocked on hardware for a local open-weight vision model).
#
# When implemented, evidence from this engine MUST use
# ConfidenceSource.VISION_MODEL, never OCR_ENGINE. A vision model's
# self-reported confidence is a generated token, not a measurement, and the
# two must never be compared or averaged. See core.types.Evidence.
