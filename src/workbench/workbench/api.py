"""
Workbench Intake API Interface.

Owned by: Developer 1 (System Architect)
Subsystem: workbench
"""

from typing import Any, Dict
from workbench.planner.schemas import TaskRequest


class WorkbenchAPI:
    """
    Main entrypoint interface for external clients to submit tasks to the workbench.
    """

    def submit_task(self, raw_input: Dict[str, Any]) -> TaskRequest:
        """
        Receives user payload, converts to TaskRequest, and forwards to TaskIntake.
        """
        raise NotImplementedError("WorkbenchAPI.submit_task will be implemented by Developer 1.")
