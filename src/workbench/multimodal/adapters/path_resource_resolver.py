"""
Filesystem resolver for ResourceReference. SECURITY BOUNDARY.

Owned by: Developer 4 (Multimodal Engineer)

ResourceReference.uri_or_path arrives from outside this subsystem. It is a
REQUEST to read something, never an authorisation to read it. This adapter
therefore:

  1. resolves the path fully (following .. and symlinks), then
  2. requires the result to sit inside a configured allowed root, then
  3. requires the resource_type to be permitted, then
  4. refuses every URI scheme, since zero-egress forbids network fetches.

Deny by default: with no allowed roots configured, nothing resolves.

Read tests/unit/multimodal/test_resolver_security.py before touching this
file. Those tests are the security boundary; do not weaken them.
"""

import logging
from pathlib import Path
from typing import Iterable, Optional, Sequence

from workbench.core.types import ResourceReference, ResourceType
from workbench.multimodal.errors import (
    ResourceAccessDeniedError,
    ResourceResolutionError,
)
from workbench.multimodal.ports.resource_resolver import ResolvedResource

logger = logging.getLogger(__name__)

_PDF_SUFFIXES = {".pdf"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}

DEFAULT_ALLOWED_TYPES = (
    ResourceType.USER_PROVIDED,
    ResourceType.RETRIEVED,
    ResourceType.GENERATED_ARTIFACT,
    ResourceType.CONTROLLED_LOCAL,
)

_MAX_BYTES = 256 * 1024 * 1024


class PathResourceResolver:
    def __init__(
        self,
        allowed_roots: Iterable[str | Path],
        allowed_types: Sequence[ResourceType] = DEFAULT_ALLOWED_TYPES,
        max_bytes: int = _MAX_BYTES,
    ) -> None:
        self._roots = [Path(root).resolve() for root in allowed_roots]
        self._allowed_types = tuple(allowed_types)
        self._max_bytes = max_bytes

    def resolve(self, resource: ResourceReference) -> ResolvedResource:
        path = self._validated_path(resource)

        try:
            size = path.stat().st_size
            if size > self._max_bytes:
                raise ResourceResolutionError(
                    f"Resource exceeds {self._max_bytes} byte limit: {size} bytes"
                )
            content = path.read_bytes()
        except OSError as exc:
            raise ResourceResolutionError(f"Resource unreadable: {exc}") from exc

        suffix = path.suffix.lower()
        return ResolvedResource(
            resource_id=resource.resource_id,
            content=content,
            filename=path.name,
            media_type=_MEDIA_TYPES.get(suffix),
            is_pdf=suffix in _PDF_SUFFIXES,
            is_image=suffix in _IMAGE_SUFFIXES,
        )

    # -- security ----------------------------------------------------------

    def _validated_path(self, resource: ResourceReference) -> Path:
        if resource.resource_type not in self._allowed_types:
            raise ResourceAccessDeniedError(
                f"Resource type not permitted: {resource.resource_type}"
            )

        raw = (resource.uri_or_path or "").strip()
        if not raw:
            raise ResourceAccessDeniedError("Empty resource path")

        # Zero-egress: no scheme is ever followed, including file://, which
        # would otherwise be a second way to express an absolute path.
        if "://" in raw:
            raise ResourceAccessDeniedError(
                f"URI schemes are not permitted (zero-egress): {raw!r}"
            )

        if "\x00" in raw:
            raise ResourceAccessDeniedError("Null byte in resource path")

        if not self._roots:
            raise ResourceAccessDeniedError(
                "No allowed roots configured; refusing all resource access"
            )

        try:
            # strict=False so a non-existent path still normalises and is
            # judged by the SAME containment rule as an existing one.
            candidate = Path(raw).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ResourceAccessDeniedError(f"Unresolvable path: {exc}") from exc

        if not any(self._is_within(candidate, root) for root in self._roots):
            logger.warning(
                "denied resource outside allowed roots: resource_id=%s",
                resource.resource_id,
            )
            raise ResourceAccessDeniedError(
                f"Path is outside the permitted roots: {candidate}"
            )

        if not candidate.is_file():
            raise ResourceResolutionError(f"Not a file: {candidate}")

        return candidate

    @staticmethod
    def _is_within(candidate: Path, root: Path) -> bool:
        try:
            return candidate == root or candidate.is_relative_to(root)
        except ValueError:
            return False
