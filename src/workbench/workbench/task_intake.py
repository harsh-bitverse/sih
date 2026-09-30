"""
Task Intake Implementation.

Owned by: Developer 1 (System Architect)
Subsystem: workbench
"""

from typing import Optional

from workbench.planner.schemas import TaskRequest
from workbench.workbench.validation import TaskValidator


class TaskIntake:
    """
    Handles user task intake, preliminary resource resolution, and context initialization.
    """

    def __init__(self, validator: Optional[TaskValidator] = None) -> None:
        self.validator = validator or TaskValidator()

    def ingest_task(self, request: TaskRequest) -> TaskRequest:
        """
        Validates and ingests a raw TaskRequest from the API/UI.
        """
        self.validator.validate(request)
        return request
