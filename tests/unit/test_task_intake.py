"""
Unit Tests for Workbench Task Intake & UI Boundary.

Owned by: Developer 1 (System Architect)
"""

import pytest

from workbench.core.context import RequestContext
from workbench.core.errors import ContractValidationError
from workbench.core.types import ResourceReference, ResourceType
from workbench.planner.schemas import TaskRequest
from workbench.workbench.api import WorkbenchAPI
from workbench.workbench.task_intake import TaskIntake
from workbench.workbench.validation import TaskValidator
from workbench.ui.task_intake_ui import TaskIntakeUI


def test_valid_task_creates_task_request():
    """
    TEST 1: Valid task payload creates a valid TaskRequest.
    """
    api = WorkbenchAPI()
    raw_payload = {
        "user_input": "Analyze the attached inspection package for equipment E-204.",
        "requested_output_info": {"format": "docx", "description": "Corrective action proposal."},
        "user_id": "engineer_01",
    }
    task_req = api.submit_task(raw_payload)

    assert isinstance(task_req, TaskRequest)
    assert task_req.user_input == raw_payload["user_input"]
    assert task_req.request_context.user_id == "engineer_01"


def test_empty_task_rejected():
    """
    TEST 2: Empty task description is rejected with ContractValidationError.
    """
    validator = TaskValidator()
    context = RequestContext(request_id="req-1", task_id="task-1", user_id="u-1", source_component="test")
    req = TaskRequest(request_context=context, user_input="")

    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate(req)

    assert "cannot be empty" in str(exc_info.value)


def test_whitespace_only_task_rejected():
    """
    TEST 3: Whitespace-only task description is rejected with ContractValidationError.
    """
    validator = TaskValidator()
    context = RequestContext(request_id="req-1", task_id="task-1", user_id="u-1", source_component="test")
    req = TaskRequest(request_context=context, user_input="   \n \t  ")

    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate(req)

    assert "cannot be empty or only whitespace" in str(exc_info.value)


def test_resources_are_preserved():
    """
    TEST 4: Resources attached to task intake are preserved in TaskRequest.
    """
    api = WorkbenchAPI()
    res = ResourceReference(
        resource_id="res-e204-pdf",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/uploads/e204_inspection.pdf",
    )
    task_req = api.submit_task({
        "user_input": "Analyze equipment E-204.",
        "resources": [res],
    })

    assert len(task_req.resources) == 1
    assert task_req.resources[0].resource_id == "res-e204-pdf"
    assert task_req.resources[0].uri_or_path == "data/uploads/e204_inspection.pdf"


def test_requested_output_info_is_preserved():
    """
    TEST 5: requested_output_info is preserved.
    """
    api = WorkbenchAPI()
    output_info = {"format": "pdf", "description": "Summary report", "confidential": True}
    task_req = api.submit_task({
        "user_input": "Generate summary report.",
        "requested_output_info": output_info,
    })

    assert task_req.requested_output_info == output_info


def test_request_context_is_created_correctly():
    """
    TEST 6: RequestContext is created correctly with task_id, request_id, user_id, source_component.
    """
    api = WorkbenchAPI()
    task_req = api.submit_task({
        "user_input": "Calculate pipeline pressure drop.",
        "user_id": "operator_42",
    })

    ctx = task_req.request_context
    assert ctx.task_id.startswith("task-")
    assert ctx.request_id.startswith("req-")
    assert ctx.user_id == "operator_42"
    assert ctx.source_component == "workbench_api"


def test_invalid_resource_is_rejected():
    """
    TEST 7: Invalid resource with empty resource_id or uri_or_path is rejected.
    """
    validator = TaskValidator()
    context = RequestContext(request_id="req-1", task_id="task-1", user_id="u-1", source_component="test")
    invalid_res = ResourceReference(
        resource_id="",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/uploads/doc.pdf",
    )
    req = TaskRequest(request_context=context, user_input="Valid prompt", resources=[invalid_res])

    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate(req)

    assert "resource_id" in str(exc_info.value)


def test_task_request_preserves_original_user_input_exactly():
    """
    TEST 8: TaskRequest preserves original user input string exactly.
    """
    api = WorkbenchAPI()
    exact_prompt = "  Analyze findings from inspection report #402, review SOP-101, and output docx format.  "
    task_req = api.submit_task({"user_input": exact_prompt})

    assert task_req.user_input == exact_prompt


def test_task_id_request_id_are_present():
    """
    TEST 9: task_id and request_id are present on TaskRequest.request_context.
    """
    api = WorkbenchAPI()
    task_req = api.submit_task({"user_input": "Test task"})

    assert task_req.request_context.task_id is not None
    assert len(task_req.request_context.task_id) > 0
    assert task_req.request_context.request_id is not None
    assert len(task_req.request_context.request_id) > 0


def test_no_planner_workflow_execution_occurs_during_intake():
    """
    TEST 10: Task intake only creates and validates TaskRequest, without executing Planner or Workflow Engine.
    """
    api = WorkbenchAPI()
    task_req = api.submit_task({"user_input": "Inspect boiler valves."})

    # Verify return type is pure TaskRequest
    assert isinstance(task_req, TaskRequest)
    # Verify no execution plan or workflow state is returned or attached
    assert not hasattr(task_req, "execution_plan")
    assert not hasattr(task_req, "workflow_state")


def test_ui_component_layout_and_submission():
    """
    TEST 11 & 12: TaskIntakeUI provides layout metadata and delegates form submission to WorkbenchAPI.
    """
    ui = TaskIntakeUI()
    layout = ui.get_layout()

    assert layout["title"] == "SOVEREIGN AI WORKBENCH"
    assert len(layout["sections"]) == 3
    assert "Submit Task" in layout["actions"]

    res = ResourceReference(
        resource_id="res-ui-001",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/uploads/ui_doc.pdf",
    )
    task_req = ui.submit(
        user_input="Task submitted from UI boundary.",
        resources=[res],
        requested_output_info={"format": "pdf"},
        user_id="ui_user_01",
    )

    assert isinstance(task_req, TaskRequest)
    assert task_req.user_input == "Task submitted from UI boundary."
    assert task_req.request_context.user_id == "ui_user_01"
