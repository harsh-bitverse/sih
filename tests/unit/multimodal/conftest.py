"""Shared fixtures for multimodal unit tests."""

import pytest

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference, ResourceType
from workbench.multimodal.adapters.path_resource_resolver import PathResourceResolver
from workbench.multimodal.errors import ArtifactStoreError
from workbench.multimodal.ports.ocr_backend import OcrWord, PixelBox

from tests.unit.multimodal.fixtures_builder import (
    write_digital_pdf,
    write_photograph,
    write_scanned_pdf,
)


# -- test doubles ---------------------------------------------------------

class FakeOcrBackend:
    """Deterministic, fast, needs no binary."""

    def __init__(self, words=None):
        self._words = words if words is not None else self._default_words()
        self.calls = 0

    @property
    def name(self) -> str:
        return "fake-ocr-1.0"

    def recognize(self, image):
        self.calls += 1
        return list(self._words)

    @staticmethod
    def _default_words():
        return [
            OcrWord("Surface", PixelBox(100, 200, 90, 30), 0.95, "1-1-1"),
            OcrWord("corrosion", PixelBox(200, 200, 120, 30), 0.91, "1-1-1"),
            OcrWord("Flange", PixelBox(100, 260, 80, 30), 0.40, "1-1-2"),
        ]


class EmptyOcrBackend(FakeOcrBackend):
    def recognize(self, image):
        self.calls += 1
        return []


class ExplodingOcrBackend(FakeOcrBackend):
    def recognize(self, image):
        raise RuntimeError("backend blew up")


class InMemoryArtifactStore:
    """Same contract as LocalArtifactStore, no filesystem."""

    def __init__(self):
        self._items = {}

    def put(self, content: bytes, media_type: str = "image/png") -> str:
        import hashlib
        artifact_id = f"art_{hashlib.sha256(content).hexdigest()[:24]}"
        self._items[artifact_id] = content
        return artifact_id

    def get(self, artifact_id: str) -> bytes:
        if artifact_id not in self._items:
            raise ArtifactStoreError(f"No such artifact: {artifact_id}")
        return self._items[artifact_id]

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._items

    def location_of(self, artifact_id: str) -> str:
        return f"memory://{artifact_id}"


# -- fixtures -------------------------------------------------------------

@pytest.fixture(scope="session")
def documents(tmp_path_factory):
    """Generated once per session; never committed to the repo."""
    root = tmp_path_factory.mktemp("multimodal_docs")
    return {
        "scanned": write_scanned_pdf(root / "scanned_inspection_report.pdf"),
        "digital": write_digital_pdf(root / "digital_text.pdf"),
        "photo": write_photograph(root / "valve_tag.png"),
        "root": root,
    }


@pytest.fixture
def resolver(documents):
    return PathResourceResolver(allowed_roots=[documents["root"]])


@pytest.fixture
def store():
    return InMemoryArtifactStore()


@pytest.fixture
def backend():
    return FakeOcrBackend()


@pytest.fixture
def context():
    return RequestContext(
        request_id="req-001",
        task_id="task-042",
        user_id="ridhimaa",
        step_id="step-2",
        source_component="orchestrator",
    )


@pytest.fixture
def scanned_resource(documents):
    return ResourceReference(
        resource_id="res_scanned",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path=str(documents["scanned"]),
    )


@pytest.fixture
def photo_resource(documents):
    return ResourceReference(
        resource_id="res_photo",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path=str(documents["photo"]),
    )


@pytest.fixture
def digital_resource(documents):
    return ResourceReference(
        resource_id="res_digital",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path=str(documents["digital"]),
    )
