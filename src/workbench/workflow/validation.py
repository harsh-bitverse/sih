"""
Workflow Step Validation.

Owned by: Developer 1 (System Architect)
Subsystem: workflow
"""

from pydantic import BaseModel, Field

from workbench.models.interfaces import AgentResult
from workbench.planner.schemas import ExecutionStep


class StepValidationResult(BaseModel):
    """
    Result of validating an AgentResult against an ExecutionStep's
    planner-defined passing criteria.
    """

    passed: bool = Field(
        description="Whether the step satisfies its passing criteria"
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="Reasons explaining the validation outcome",
    )


class StepValidator:
    """
    Validates agent results against Planner-provided passing criteria.

    The validator does not define success criteria itself. It evaluates
    the criteria explicitly provided by the Planner.
    """

    SUPPORTED_CRITERIA = {
        "min_evidence_count",
        "min_artifact_count",
        "agent_status",
    }

    def validate_step_result(
        self,
        step: ExecutionStep,
        agent_result: AgentResult,
    ) -> StepValidationResult:
        """
        Evaluate an AgentResult against the step's passing criteria.
        """

        criteria = step.passing_criteria

        if not criteria:
            return StepValidationResult(
                passed=True,
                reasons=["No passing criteria specified."],
            )

        reasons: list[str] = []
        passed = True

        for criterion, expected_value in criteria.items():

            if criterion not in self.SUPPORTED_CRITERIA:
                passed = False
                reasons.append(
                    f"Unsupported passing criterion: '{criterion}'."
                )
                continue

            if criterion == "min_evidence_count":
                actual_count = len(agent_result.result_evidence)

                if actual_count < expected_value:
                    passed = False
                    reasons.append(
                        f"Evidence count {actual_count} is below the "
                        f"required minimum of {expected_value}."
                    )
                else:
                    reasons.append(
                        f"Evidence count requirement satisfied: "
                        f"{actual_count} >= {expected_value}."
                    )

            elif criterion == "min_artifact_count":
                actual_count = len(agent_result.artifacts)

                if actual_count < expected_value:
                    passed = False
                    reasons.append(
                        f"Artifact count {actual_count} is below the "
                        f"required minimum of {expected_value}."
                    )
                else:
                    reasons.append(
                        f"Artifact count requirement satisfied: "
                        f"{actual_count} >= {expected_value}."
                    )

            elif criterion == "agent_status":
                actual_status = agent_result.status.value

                if actual_status != expected_value:
                    passed = False
                    reasons.append(
                        f"Agent status '{actual_status}' does not match "
                        f"required status '{expected_value}'."
                    )
                else:
                    reasons.append(
                        f"Agent status requirement satisfied: "
                        f"{actual_status}."
                    )

        return StepValidationResult(
            passed=passed,
            reasons=reasons,
        )