"""
Unit tests for the Planner.

Owned by: Developer 1 (System Architect)
Subsystem: planner

These tests verify the deterministic Planner implementation,
including both single-step fallback behavior and the
multi-step inspection-analysis workflow.
"""

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference, ResourceType
from workbench.planner.planner import Planner
from workbench.planner.schemas import TaskRequest


def create_context() -> RequestContext:
    return RequestContext(
        request_id="req-planner-test",
        task_id="task-planner-test",
        user_id="test-user",
        source_component="test",
    )


def create_request(
    user_input: str = "Analyze the inspection report.",
    resources=None,
    requested_output_info=None,
) -> TaskRequest:
    if resources is None:
        resources = []

    if requested_output_info is None:
        requested_output_info = {}

    return TaskRequest(
        request_context=create_context(),
        user_input=user_input,
        resources=resources,
        requested_output_info=requested_output_info,
    )


# ---------------------------------------------------------------------------
# Single-step fallback Planner tests
# ---------------------------------------------------------------------------

def test_create_plan_preserves_request_context():
    planner = Planner()
    request = create_request()

    plan = planner.create_plan(request)

    assert plan.request_context == request.request_context


def test_create_plan_preserves_task_description():
    planner = Planner()

    request = create_request(
        user_input="Analyze the inspection report and identify safety findings."
    )

    plan = planner.create_plan(request)

    assert plan.task_description == request.user_input


def test_create_plan_creates_one_executable_step_for_generic_task():
    planner = Planner()

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline."
    )

    plan = planner.create_plan(request)

    assert len(plan.executable_steps) == 1


def test_created_step_uses_user_input_as_objective_for_generic_task():
    planner = Planner()

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline."
    )

    plan = planner.create_plan(request)

    step = plan.executable_steps[0]

    assert step.step_id == "step-1"
    assert step.objective == request.user_input


def test_created_step_preserves_resources():
    planner = Planner()

    resource = ResourceReference(
        resource_id="resource-1",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/demo/inspection_report.pdf",
        provenance={
            "source": "user_upload",
        },
    )

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline.",
        resources=[resource],
    )

    plan = planner.create_plan(request)

    step = plan.executable_steps[0]

    assert step.resources == request.resources
    assert step.resources[0].resource_id == "resource-1"


def test_requested_output_information_is_used():
    planner = Planner()

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline.",
        requested_output_info={
            "format": "docx",
            "description": "Generate a calculation report.",
        },
    )

    plan = planner.create_plan(request)

    step = plan.executable_steps[0]

    assert step.expected_output == str(request.requested_output_info)


def test_default_expected_output_is_used_when_not_specified():
    planner = Planner()

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline."
    )

    plan = planner.create_plan(request)

    step = plan.executable_steps[0]

    assert step.expected_output == "Complete the requested task."


def test_created_step_requires_successful_agent_status():
    planner = Planner()

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline."
    )

    plan = planner.create_plan(request)

    step = plan.executable_steps[0]

    assert step.passing_criteria == {
        "agent_status": "SUCCESS",
    }


def test_created_step_has_no_dependencies():
    planner = Planner()

    request = create_request(
        user_input="Calculate the pressure drop across the pipeline."
    )

    plan = planner.create_plan(request)

    step = plan.executable_steps[0]

    assert step.dependencies == []


# ---------------------------------------------------------------------------
# Multi-step inspection-analysis Planner tests
# ---------------------------------------------------------------------------

def create_inspection_request() -> TaskRequest:
    return create_request(
        user_input=(
            "Analyze the inspection report, identify safety findings, "
            "determine applicable SOP requirements, review previous incidents, "
            "recommend corrective actions, and prepare an approval proposal."
        ),
        requested_output_info={
            "format": "docx",
            "description": "Corrective-action proposal for approval.",
        },
    )


def test_inspection_task_creates_six_executable_steps():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    assert len(plan.executable_steps) == 6


def test_inspection_plan_preserves_request_context():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    assert plan.request_context == request.request_context
    assert plan.task_description == request.user_input


def test_inspection_plan_has_expected_step_ids():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    step_ids = [step.step_id for step in plan.executable_steps]

    assert step_ids == [
        "step-1",
        "step-2",
        "step-3",
        "step-4",
        "step-5",
        "step-6",
    ]


def test_inspection_plan_has_expected_dependencies():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    dependencies = {
        step.step_id: step.dependencies
        for step in plan.executable_steps
    }

    assert dependencies == {
        "step-1": [],
        "step-2": [],
        "step-3": ["step-1", "step-2"],
        "step-4": [],
        "step-5": ["step-3", "step-4"],
        "step-6": ["step-5"],
    }


def test_inspection_plan_all_steps_have_objectives():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    for step in plan.executable_steps:
        assert step.objective.strip() != ""


def test_inspection_plan_all_steps_have_expected_outputs():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    for step in plan.executable_steps:
        assert step.expected_output.strip() != ""


def test_inspection_plan_all_steps_require_successful_agent_status():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    for step in plan.executable_steps:
        assert step.passing_criteria == {
            "agent_status": "SUCCESS",
        }


def test_inspection_plan_passes_resources_to_each_step():
    planner = Planner()

    resource = ResourceReference(
        resource_id="inspection-package",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/demo/inspection_report.pdf",
        provenance={
            "source": "user_upload",
        },
    )

    request = create_request(
        user_input=(
            "Analyze the inspection report, identify safety findings, "
            "determine applicable SOP requirements, review previous incidents, "
            "recommend corrective actions, and prepare an approval proposal."
        ),
        resources=[resource],
    )

    plan = planner.create_plan(request)

    for step in plan.executable_steps:
        assert step.resources == request.resources


def test_inspection_final_step_uses_requested_output():
    planner = Planner()

    request = create_inspection_request()

    plan = planner.create_plan(request)

    final_step = plan.executable_steps[-1]

    assert final_step.expected_output == str(
        request.requested_output_info
    )