"""
Port: storage for artifacts this subsystem derives (rendered pages, crops).

Owned by: Developer 4 (Multimodal Engineer)

An evidence region is meaningless without the image it refers to, so derived
images must remain retrievable at audit time.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, content: bytes, media_type: str = "image/png") -> str:
        """Store bytes, return a deterministic artifact_id.

        Deterministic: identical bytes yield the same id, so re-running an
        extraction reproduces the same references and audits stay stable.
        """
        ...

    def get(self, artifact_id: str) -> bytes:
        ...

    def exists(self, artifact_id: str) -> bool:
        ...

    def location_of(self, artifact_id: str) -> str:
        """Storage URI for core Artifact.location."""
        ...
