"""
SIH Sovereign On-Premise Agentic AI Workbench - Demo Composition Subsystem.

Provides composition roots, synthetic MRPL equipment demo data, and entrypoints
for end-to-end workbench validation.
"""

from workbench.demo.composition import DemoComposition
from workbench.demo.data import (
    E204_TASK_PROMPT,
    create_mrpl_e204_resources,
    create_mrpl_e204_task_request,
)

__all__ = [
    "DemoComposition",
    "E204_TASK_PROMPT",
    "create_mrpl_e204_resources",
    "create_mrpl_e204_task_request",
]
