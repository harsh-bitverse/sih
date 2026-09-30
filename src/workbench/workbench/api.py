"""
Workbench Intake API Implementation.

Owned by: Developer 1 (System Architect)
Subsystem: workbench
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference
from workbench.planner.schemas import TaskRequest
from workbench.workbench.task_intake import TaskIntake


class WorkbenchAPI:
    """
    Main entrypoint service for external clients and UI to submit tasks to the workbench.
    Converts raw user payload into a validated TaskRequest without executing Planner or Workflow.
    """

    def __init__(self, intake: Optional[TaskIntake] = None) -> None:
        self.intake = intake or TaskIntake()

    def submit_task(self, raw_input: Dict[str, Any]) -> TaskRequest:
        """
        Receives raw user payload, constructs RequestContext and TaskRequest, and validates via TaskIntake.
        """
        if not isinstance(raw_input, dict):
            raw_input = {}

        user_input = raw_input.get("user_input", "")
        user_id = raw_input.get("user_id", "workbench_user")

        ctx = raw_input.get("request_context")
        if not isinstance(ctx, RequestContext):
            ctx = RequestContext(
                request_id=f"req-{uuid4()}",
                task_id=f"task-{uuid4()}",
                user_id=user_id,
                source_component="workbench_api",
            )

        raw_resources = raw_input.get("resources", [])
        parsed_resources: List[ResourceReference] = []
        for r in raw_resources:
            if isinstance(r, ResourceReference):
                parsed_resources.append(r)
            elif isinstance(r, dict):
                try:
                    parsed_resources.append(ResourceReference(**r))
                except Exception:
                    # Let TaskValidator report validation issues cleanly
                    parsed_resources.append(r)

        requested_output_info = raw_input.get("requested_output_info", {})

        task_request = TaskRequest(
            request_context=ctx,
            user_input=user_input,
            resources=parsed_resources,
            requested_output_info=requested_output_info,
        )

        return self.intake.ingest_task(task_request)
