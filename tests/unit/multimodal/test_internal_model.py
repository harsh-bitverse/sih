"""The internal model refuses to represent untraceable or invalid evidence."""

import pytest
from pydantic import ValidationError

from workbench.core.types import ConfidenceSource
from workbench.multimodal.pipeline.internal_model import Confidence, Region


def test_region_rejects_reversed_corners():
    with pytest.raises(ValidationError):
        Region(x0=0.9, y0=0.1, x1=0.2, y1=0.5)


def test_region_rejects_values_outside_the_page():
    with pytest.raises(ValidationError):
        Region(x0=0.0, y0=0.0, x1=1.4, y1=0.5)


def test_region_renders_a_readable_location():
    location = Region(x0=0.1, y0=0.2, x1=0.3, y1=0.4).as_location()
    assert location.startswith("bbox=(0.1000,0.2000)")


def test_confidence_requires_a_source():
    with pytest.raises(ValidationError):
        Confidence(value=0.9)


def test_confidence_rejects_impossible_values():
    with pytest.raises(ValidationError):
        Confidence(value=1.4, source=ConfidenceSource.OCR_ENGINE)
