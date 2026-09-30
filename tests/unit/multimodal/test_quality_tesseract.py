"""Quality tests: real Tesseract. Tolerant by design, and skip without it.

These check that OCR works at all, not that it is perfect.
"""

import pytest

from workbench.core.types import ConfidenceSource
from workbench.multimodal.adapters.local_artifact_store import LocalArtifactStore
from workbench.multimodal.adapters.tesseract_backend import TesseractOcrBackend
from workbench.multimodal.errors import OcrBackendUnavailableError
from workbench.multimodal.processor import DefaultMultimodalProcessor
from workbench.multimodal.schemas import (
    MultimodalRequest,
    MultimodalStatus,
)


@pytest.fixture(scope="module")
def tesseract():
    backend = TesseractOcrBackend()
    try:
        backend.name
    except OcrBackendUnavailableError:
        pytest.skip("tesseract binary not installed")
    return backend


@pytest.fixture
def real_result(tesseract, resolver, context, scanned_resource, tmp_path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    processor = DefaultMultimodalProcessor(tesseract, resolver, store, dpi=200)
    result = processor.process(
        MultimodalRequest(
            request_context=context, resource=scanned_resource, modalities=["ocr"]
        )
    )
    return result, store


def test_reads_the_equipment_tag(real_result):
    result, _ = real_result
    assert any("P-101B" in e.content for e in result.evidence)


def test_reads_the_key_observation(real_result):
    result, _ = real_result
    assert "corrosion" in " ".join(e.content for e in result.evidence).lower()


def test_status_is_success_on_a_clean_scan(real_result):
    result, _ = real_result
    assert result.status is MultimodalStatus.SUCCESS


def test_confidence_is_engine_measured_and_high(real_result):
    result, _ = real_result
    scores = [e.confidence for e in result.evidence if e.confidence is not None]
    assert sum(scores) / len(scores) > 0.7
    assert all(e.confidence_source is ConfidenceSource.OCR_ENGINE
               for e in result.evidence)


def test_audit_path_leads_from_evidence_to_the_stored_image(real_result):
    """The whole traceability claim, exercised end to end."""
    result, store = real_result
    item = result.evidence[0]
    assert store.get(item.source_artifact).startswith(b"\x89PNG")
    assert item.provenance["region"]["x1"] > item.provenance["region"]["x0"]
