"""
Task Intake Interface.

Owned by: Developer 1 (System Architect)
Subsystem: workbench
"""

from workbench.planner.schemas import TaskRequest


class TaskIntake:
    """
    Handles user task intake, preliminary resource resolution, and context initialization.
    """

    def ingest_task(self, request: TaskRequest) -> TaskRequest:
        """
        Validates and ingests a raw TaskRequest from the API/UI.
        """
        raise NotImplementedError("TaskIntake.ingest_task will be implemented by Developer 1.")
