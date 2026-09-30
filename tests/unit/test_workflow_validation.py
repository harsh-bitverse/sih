"""
Unit tests for workflow step validation.

Owned by: Developer 1 (System Architect)
"""

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.core.types import Evidence
from workbench.models.interfaces import AgentResult, AgentResultStatus
from workbench.planner.schemas import ExecutionStep
from workbench.workflow.validation import StepValidator


def create_context() -> RequestContext:
    return RequestContext(
        request_id="req-test",
        task_id="task-test",
        user_id="test-user",
        source_component="test",
    )


def create_step(passing_criteria: dict) -> ExecutionStep:
    return ExecutionStep(
        step_id="step-test",
        objective="Test objective",
        expected_output="Test output",
        passing_criteria=passing_criteria,
    )


def create_agent_result(
    status: AgentResultStatus = AgentResultStatus.SUCCESS,
    evidence_count: int = 0,
    artifact_count: int = 0,
) -> AgentResult:
    evidence = [
        Evidence(
            evidence_id=f"evidence-{i}",
            content=f"Test evidence {i}",
            evidence_type="text",
        )
        for i in range(evidence_count)
    ]

    artifacts = [
        Artifact(
            artifact_id=f"artifact-{i}",
            task_id="task-test",
            step_id="step-test",
            type=ArtifactType.DOCUMENT,
            name=f"artifact-{i}.txt",
            location=f"/tmp/artifact-{i}.txt",
            mime_type="text/plain",
            created_by="test-agent",
        )
        for i in range(artifact_count)
    ]

    return AgentResult(
        request_context=create_context(),
        status=status,
        result_evidence=evidence,
        artifacts=artifacts,
    )


def test_min_evidence_count_passes_when_requirement_is_met():
    validator = StepValidator()

    step = create_step({"min_evidence_count": 1})
    result = create_agent_result(evidence_count=1)

    validation = validator.validate_step_result(step, result)

    assert validation.passed is True


def test_min_evidence_count_fails_when_requirement_is_not_met():
    validator = StepValidator()

    step = create_step({"min_evidence_count": 2})
    result = create_agent_result(evidence_count=1)

    validation = validator.validate_step_result(step, result)

    assert validation.passed is False
    assert any(
        "below the required minimum" in reason
        for reason in validation.reasons
    )


def test_min_artifact_count_passes_when_requirement_is_met():
    validator = StepValidator()

    step = create_step({"min_artifact_count": 1})
    result = create_agent_result(artifact_count=1)

    validation = validator.validate_step_result(step, result)

    assert validation.passed is True


def test_min_artifact_count_fails_when_requirement_is_not_met():
    validator = StepValidator()

    step = create_step({"min_artifact_count": 2})
    result = create_agent_result(artifact_count=1)

    validation = validator.validate_step_result(step, result)

    assert validation.passed is False
    assert any(
        "below the required minimum" in reason
        for reason in validation.reasons
    )


def test_agent_status_passes_when_status_matches():
    validator = StepValidator()

    step = create_step({"agent_status": "SUCCESS"})
    result = create_agent_result(status=AgentResultStatus.SUCCESS)

    validation = validator.validate_step_result(step, result)

    assert validation.passed is True


def test_agent_status_fails_when_status_does_not_match():
    validator = StepValidator()

    step = create_step({"agent_status": "SUCCESS"})
    result = create_agent_result(status=AgentResultStatus.FAILED)

    validation = validator.validate_step_result(step, result)

    assert validation.passed is False
    assert any(
        "does not match" in reason
        for reason in validation.reasons
    )


def test_unsupported_criterion_fails_explicitly():
    validator = StepValidator()

    step = create_step({"unknown_criterion": True})
    result = create_agent_result()

    validation = validator.validate_step_result(step, result)

    assert validation.passed is False
    assert any(
        "Unsupported passing criterion" in reason
        for reason in validation.reasons
    )


def test_empty_passing_criteria_passes():
    validator = StepValidator()

    step = create_step({})
    result = create_agent_result()

    validation = validator.validate_step_result(step, result)

    assert validation.passed is True
    assert validation.reasons == ["No passing criteria specified."]