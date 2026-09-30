"""
Task Intake Validation Implementation.

Owned by: Developer 1 (System Architect)
Subsystem: workbench
"""

from workbench.core.errors import ContractValidationError
from workbench.planner.schemas import TaskRequest


class TaskValidator:
    """
    Validates input TaskRequests against system requirements and core schemas.
    """

    def validate(self, request: TaskRequest) -> bool:
        """
        Validates task request parameters, resources, and request context.
        Raises ContractValidationError if validation fails.
        """
        if not isinstance(request, TaskRequest):
            raise ContractValidationError("Input must be a valid TaskRequest instance.")

        if not request.user_input or not request.user_input.strip():
            raise ContractValidationError("Task description cannot be empty or only whitespace.")

        ctx = request.request_context
        if not ctx or not ctx.task_id or not ctx.request_id or not ctx.user_id:
            raise ContractValidationError("Task request context must contain valid task_id, request_id, and user_id.")

        for res in request.resources:
            if not res.resource_id or not res.resource_id.strip():
                raise ContractValidationError("ResourceReference must have a non-empty resource_id.")
            if not res.uri_or_path or not res.uri_or_path.strip():
                raise ContractValidationError("ResourceReference must have a non-empty uri_or_path.")

        if not isinstance(request.requested_output_info, dict):
            raise ContractValidationError("requested_output_info must be a dictionary.")

        return True
