"""
Multimodal subsystem error hierarchy.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal

Every error here descends from a core WorkbenchError so the workflow engine
can catch subsystem failures uniformly without importing our internals.
Security denials descend from SecurityViolationError so the audit subsystem
sees them as policy events, not ordinary faults.
"""

from workbench.core.errors import SecurityViolationError, SubsystemExecutionError


class MultimodalError(SubsystemExecutionError):
    """Base for recoverable multimodal processing failures."""


class DocumentUnreadableError(MultimodalError):
    """File missing, corrupt, or not a document we can open."""


class DocumentEncryptedError(MultimodalError):
    """Password-protected. We never attempt to crack or guess."""


class OcrBackendUnavailableError(MultimodalError):
    """The OCR backend is not installed or not reachable."""


class ArtifactStoreError(MultimodalError):
    """A derived artifact could not be stored or retrieved."""


class ResourceResolutionError(MultimodalError):
    """A ResourceReference is registered/allowed but could not be read."""


class ResourceAccessDeniedError(SecurityViolationError):
    """SECURITY: the resource path fell outside the permitted roots.

    Deliberately a SecurityViolationError, not a MultimodalError: a denied
    path is a policy event that the audit subsystem must be able to see.
    """
