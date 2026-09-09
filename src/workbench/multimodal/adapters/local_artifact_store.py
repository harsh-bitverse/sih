"""
Content-addressed artifact store on the local filesystem.

Owned by: Developer 4 (Multimodal Engineer)

Content addressing gives deterministic IDs and free deduplication: the same
rendered page yields the same artifact_id on every run, which is what makes
an audit reproducible.
"""

import hashlib
import logging
from pathlib import Path

from workbench.multimodal.errors import ArtifactStoreError

logger = logging.getLogger(__name__)

ARTIFACT_ID_PREFIX = "art_"
_HASH_CHARS = 24


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class LocalArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, artifact_id: str) -> Path:
        # An artifact id is never interpolated into a path without this check:
        # ids can reach us from outside and must not become traversal.
        if not artifact_id.startswith(ARTIFACT_ID_PREFIX):
            raise ArtifactStoreError(f"Malformed artifact id: {artifact_id!r}")
        stem = artifact_id[len(ARTIFACT_ID_PREFIX):]
        if not stem.isalnum():
            raise ArtifactStoreError(f"Malformed artifact id: {artifact_id!r}")
        return self._root / f"{stem}.bin"

    def put(self, content: bytes, media_type: str = "image/png") -> str:
        artifact_id = f"{ARTIFACT_ID_PREFIX}{content_hash(content)[:_HASH_CHARS]}"
        path = self._path_for(artifact_id)
        if not path.exists():
            try:
                path.write_bytes(content)
            except OSError as exc:
                raise ArtifactStoreError(f"Could not write {path}: {exc}") from exc
            logger.debug("stored artifact %s (%d bytes)", artifact_id, len(content))
        return artifact_id

    def get(self, artifact_id: str) -> bytes:
        path = self._path_for(artifact_id)
        if not path.is_file():
            raise ArtifactStoreError(f"No such artifact: {artifact_id}")
        return path.read_bytes()

    def exists(self, artifact_id: str) -> bool:
        try:
            return self._path_for(artifact_id).is_file()
        except ArtifactStoreError:
            return False

    def location_of(self, artifact_id: str) -> str:
        return str(self._path_for(artifact_id))
