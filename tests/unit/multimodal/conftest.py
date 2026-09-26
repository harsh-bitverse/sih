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


# -- vision test doubles --------------------------------------------------

from workbench.multimodal.errors import VisionModelUnavailableError  # noqa: E402
from workbench.multimodal.ports.vision_model import VisionModelResponse  # noqa: E402

GOOD_VISION_JSON = (
    '{"observations": ['
    '{"observation": "Surface corrosion near lower flange", "category": "corrosion", '
    '"region": [0.10, 0.55, 0.40, 0.80], "confidence": 0.82},'
    '{"observation": "Tag plate reads V-204", "category": "label", '
    '"region": null, "confidence": null}'
    ']}'
)


class ScriptedVisionClient:
    """Returns scripted responses in order; the last one repeats.

    Each script entry is either response text or an Exception to raise.
    Records every prompt so tests can inspect what the model was told.
    """

    def __init__(self, script=None, box_scale: float = 1.0, name="fake-vlm-1.0"):
        self._script = list(script) if script is not None else [GOOD_VISION_JSON]
        self._box_scale = box_scale
        self._name = name
        self.prompts = []

    @property
    def name(self) -> str:
        return self._name

    def generate(self, image_png, prompt, max_output_tokens=None):
        self.prompts.append(prompt)
        index = min(len(self.prompts) - 1, len(self._script) - 1)
        step = self._script[index]
        if isinstance(step, Exception):
            raise step
        return VisionModelResponse(
            text=step, model_name=self._name, box_scale=self._box_scale
        )

    @property
    def calls(self) -> int:
        return len(self.prompts)


@pytest.fixture
def vision_client():
    return ScriptedVisionClient()


@pytest.fixture
def unavailable_client():
    return ScriptedVisionClient(script=[VisionModelUnavailableError("GPU host down")])
