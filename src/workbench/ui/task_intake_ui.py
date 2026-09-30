"""
Workbench Task Intake UI Component.

Owned by: Developer 1 (System Architect)
Subsystem: ui

Provides the user-facing task intake boundary for capturing task prompts, attaching resources,
and specifying deliverable metadata. Interacts strictly with WorkbenchAPI / TaskIntake.
Does NOT directly invoke Planner, Workflow Engine, or Model Registry.
"""

from typing import Any, Dict, List, Optional

from workbench.core.types import ResourceReference
from workbench.planner.schemas import TaskRequest
from workbench.workbench.api import WorkbenchAPI


class TaskIntakeUI:
    """
    User Interface component for Workbench Task Intake.
    """

    def __init__(self, api: Optional[WorkbenchAPI] = None) -> None:
        self.api = api or WorkbenchAPI()

    def get_layout(self) -> Dict[str, Any]:
        """
        Returns conceptual UI layout schema.
        """
        return {
            "title": "SOVEREIGN AI WORKBENCH",
            "sections": [
                {
                    "id": "task_prompt",
                    "label": "Task Description",
                    "placeholder": "Describe what you want the Workbench to do...",
                },
                {
                    "id": "resources",
                    "label": "Resources",
                    "action": "+ Upload / Add Resource",
                },
                {
                    "id": "requested_output",
                    "label": "Requested Output",
                    "fields": ["format", "description"],
                },
            ],
            "actions": ["Validate Task", "Submit Task"],
        }

    def validate_input(
        self,
        user_input: str,
        resources: Optional[List[ResourceReference]] = None,
        requested_output_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Validates form inputs before submission.
        """
        try:
            self.api.submit_task({
                "user_input": user_input,
                "resources": resources or [],
                "requested_output_info": requested_output_info or {},
            })
            return True
        except Exception:
            return False

    def submit(
        self,
        user_input: str,
        resources: Optional[List[ResourceReference]] = None,
        requested_output_info: Optional[Dict[str, Any]] = None,
        user_id: str = "workbench_user",
    ) -> TaskRequest:
        """
        Submits the Task Intake form, delegating TaskRequest creation and validation
        to WorkbenchAPI. Does NOT invoke Planner or Workflow Engine.
        """
        payload = {
            "user_input": user_input,
            "resources": resources or [],
            "requested_output_info": requested_output_info or {},
            "user_id": user_id,
        }
        return self.api.submit_task(payload)
