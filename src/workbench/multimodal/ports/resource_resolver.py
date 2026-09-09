"""
Port: turning a ResourceReference into bytes.

Owned by: Developer 4 (Multimodal Engineer)

SECURITY: a ResourceReference carries uri_or_path, but that path is a REQUEST,
not an authorisation. Adapters must validate it against configured allowed
roots before reading anything. See adapters/path_resource_resolver.py.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from workbench.core.types import ResourceReference


@dataclass(frozen=True)
class ResolvedResource:
    """Content plus the identity needed to build provenance."""
    resource_id: str
    content: bytes
    filename: Optional[str] = None
    media_type: Optional[str] = None
    is_pdf: bool = False
    is_image: bool = False


@runtime_checkable
class ResourceResolver(Protocol):
    def resolve(self, resource: ResourceReference) -> ResolvedResource:
        """Resolve an allowed resource.

        Raises ResourceAccessDeniedError if the path is outside policy.
        Raises ResourceResolutionError if allowed but unreadable.
        """
        ...
