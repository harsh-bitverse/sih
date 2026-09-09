"""SECURITY: uri_or_path is a request to read, never an authorisation.

If these fail, whatever constructs a ResourceReference can point this
subsystem at arbitrary files. Do not weaken these tests.
"""

import pytest

from workbench.core.types import ResourceReference, ResourceType
from workbench.multimodal.adapters.path_resource_resolver import PathResourceResolver
from workbench.multimodal.errors import (
    ResourceAccessDeniedError,
    ResourceResolutionError,
)

OUTSIDE_ROOT = [
    "../../etc/passwd",
    "../../../../../../etc/shadow",
    "/etc/passwd",
    "/etc/hostname",
    "C:\\Windows\\System32\\config\\SAM",
    "",
    "   ",
]

SCHEMES = [
    "file:///etc/passwd",
    "https://evil.example.com/payload.pdf",
    "http://169.254.169.254/latest/meta-data/",
    "ftp://example.com/x.pdf",
]


def reference(path: str, resource_type=ResourceType.USER_PROVIDED):
    return ResourceReference(
        resource_id="res_probe", resource_type=resource_type, uri_or_path=path
    )


@pytest.mark.parametrize("path", OUTSIDE_ROOT)
def test_paths_outside_allowed_roots_are_denied(resolver, path):
    with pytest.raises(ResourceAccessDeniedError):
        resolver.resolve(reference(path))


@pytest.mark.parametrize("path", SCHEMES)
def test_uri_schemes_are_denied_zero_egress(resolver, path):
    with pytest.raises(ResourceAccessDeniedError):
        resolver.resolve(reference(path))


def test_traversal_out_and_back_is_denied(resolver, documents):
    """Normalisation happens before the containment check, not after."""
    sneaky = str(documents["root"]) + "/../../../etc/passwd"
    with pytest.raises(ResourceAccessDeniedError):
        resolver.resolve(reference(sneaky))


def test_null_byte_is_denied(resolver, documents):
    with pytest.raises(ResourceAccessDeniedError):
        resolver.resolve(reference(str(documents["scanned"]) + "\x00.png"))


def test_no_configured_roots_denies_everything(documents):
    """Deny by default: a misconfigured resolver refuses, it does not open up."""
    empty = PathResourceResolver(allowed_roots=[])
    with pytest.raises(ResourceAccessDeniedError):
        empty.resolve(reference(str(documents["scanned"])))


def test_disallowed_resource_type_is_denied(documents):
    restricted = PathResourceResolver(
        allowed_roots=[documents["root"]],
        allowed_types=[ResourceType.CONTROLLED_LOCAL],
    )
    with pytest.raises(ResourceAccessDeniedError):
        restricted.resolve(
            reference(str(documents["scanned"]), ResourceType.USER_PROVIDED)
        )


def test_missing_file_inside_root_is_resolution_not_security(resolver, documents):
    """Distinguish 'not allowed' from 'allowed but absent' for the audit log."""
    with pytest.raises(ResourceResolutionError):
        resolver.resolve(reference(str(documents["root"] / "nope.pdf")))


def test_oversized_file_is_refused(documents):
    tiny_limit = PathResourceResolver(allowed_roots=[documents["root"]], max_bytes=10)
    with pytest.raises(ResourceResolutionError):
        tiny_limit.resolve(reference(str(documents["scanned"])))


def test_allowed_file_resolves(resolver, documents):
    resolved = resolver.resolve(reference(str(documents["scanned"])))
    assert resolved.content.startswith(b"%PDF")
    assert resolved.is_pdf and not resolved.is_image


def test_image_is_classified(resolver, documents):
    resolved = resolver.resolve(reference(str(documents["photo"])))
    assert resolved.is_image and not resolved.is_pdf
