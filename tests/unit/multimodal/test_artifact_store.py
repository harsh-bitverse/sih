"""LocalArtifactStore: determinism, retrieval, and id hygiene."""

import pytest

from workbench.multimodal.adapters.local_artifact_store import LocalArtifactStore
from workbench.multimodal.errors import ArtifactStoreError

MALFORMED_IDS = [
    "art_../../etc/passwd",
    "../../etc/passwd",
    "art_",
    "art_abc/def",
    "art_abc.def",
    "notanartifact",
]


@pytest.fixture
def store(tmp_path):
    return LocalArtifactStore(tmp_path / "artifacts")


def test_same_bytes_give_the_same_id(store):
    assert store.put(b"page-bytes") == store.put(b"page-bytes")


def test_different_bytes_give_different_ids(store):
    assert store.put(b"page-one") != store.put(b"page-two")


def test_round_trip(store):
    artifact_id = store.put(b"page-bytes")
    assert store.get(artifact_id) == b"page-bytes"
    assert store.exists(artifact_id)


def test_missing_artifact_raises(store):
    with pytest.raises(ArtifactStoreError):
        store.get("art_" + "0" * 24)


@pytest.mark.parametrize("artifact_id", MALFORMED_IDS)
def test_malformed_ids_never_become_paths(store, artifact_id):
    """Ids can arrive from outside; they must not turn into traversal."""
    with pytest.raises(ArtifactStoreError):
        store.get(artifact_id)
    assert store.exists(artifact_id) is False


def test_location_is_reported_for_the_contract(store):
    artifact_id = store.put(b"page-bytes")
    assert artifact_id[4:] in store.location_of(artifact_id)
