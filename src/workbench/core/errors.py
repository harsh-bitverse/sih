"""
Core Workbench Exception Hierarchy.

Owned by: Developer 1 (System Architect)
Subsystem: core
"""


class WorkbenchError(Exception):
    """Base exception for all workbench domain errors."""
    pass


class ContractValidationError(WorkbenchError):
    """Raised when cross-subsystem contract or schema validation fails."""
    pass


class SecurityViolationError(WorkbenchError):
    """Raised when security policy, authorization, or zero-egress checks fail."""
    pass


class PolicyViolationError(SecurityViolationError):
    """Raised when a specific security policy rule is violated."""
    pass


class SubsystemExecutionError(WorkbenchError):
    """Raised when a subsystem encounters an unrecoverable internal error."""
    pass


class StepExecutionError(SubsystemExecutionError):
    """Raised when an execution step fails passing criteria or execution rules."""
    pass
