"""
Planner Subsystem Interface.

Owned by: Developer 1 (System Architect)
Subsystem: planner

The Planner directly decomposes a TaskRequest into meaningful executable steps
(ExecutionPlan).

There is NO separate Orchestrator in the MVP.
"""

from workbench.planner.schemas import ExecutionPlan, ExecutionStep, TaskRequest


class Planner:
    """
    Decomposes incoming TaskRequests into executable ExecutionPlans.
    """

    def create_plan(self, request: TaskRequest) -> ExecutionPlan:
        """
        Create an executable plan from a TaskRequest.

        This implementation supports the first deterministic multi-step
        decomposition for the inspection-analysis workflow.

        Other task types continue to use the original single-step behavior.
        """

        if self._is_inspection_analysis_task(request):
            return self._create_inspection_analysis_plan(request)

        return self._create_single_step_plan(request)

    def _is_inspection_analysis_task(self, request: TaskRequest) -> bool:
        """
        Detect the known inspection-analysis task shape for this
        deterministic Planner slice.

        This is intentionally simple and temporary. A future intelligent
        Planner will determine task structure through reasoning rather than
        keyword matching.
        """

        text = request.user_input.lower()

        inspection_keywords = [
            "inspection",
            "inspection report",
            "safety finding",
            "corrective action",
        ]

        return any(keyword in text for keyword in inspection_keywords)

    def _create_inspection_analysis_plan(
        self,
        request: TaskRequest,
    ) -> ExecutionPlan:
        """
        Create a meaningful multi-step plan for inspection analysis.
        """

        steps = [
            ExecutionStep(
                step_id="step-1",
                objective="Extract relevant findings from the inspection package.",
                resources=request.resources,
                expected_output=(
                    "Structured inspection findings with supporting evidence."
                ),
                passing_criteria={
                    "agent_status": "SUCCESS",
                },
            ),
            ExecutionStep(
                step_id="step-2",
                objective=(
                    "Determine the applicable SOP requirements for the "
                    "identified equipment and findings."
                ),
                resources=request.resources,
                expected_output=(
                    "Applicable SOP requirements with supporting evidence."
                ),
                passing_criteria={
                    "agent_status": "SUCCESS",
                },
            ),
            ExecutionStep(
                step_id="step-3",
                objective=(
                    "Compare the inspection findings against the applicable "
                    "SOP requirements."
                ),
                dependencies=["step-1", "step-2"],
                resources=request.resources,
                expected_output=(
                    "Comparison of findings against applicable requirements, "
                    "including identified gaps or non-conformities."
                ),
                passing_criteria={
                    "agent_status": "SUCCESS",
                },
            ),
            ExecutionStep(
                step_id="step-4",
                objective=(
                    "Review relevant historical incidents for comparable "
                    "findings and corrective actions."
                ),
                resources=request.resources,
                expected_output=(
                    "Relevant historical incidents and their associated "
                    "findings or corrective actions."
                ),
                passing_criteria={
                    "agent_status": "SUCCESS",
                },
            ),
            ExecutionStep(
                step_id="step-5",
                objective=(
                    "Formulate corrective actions based on the findings, "
                    "applicable requirements, and relevant historical evidence."
                ),
                dependencies=["step-3", "step-4"],
                resources=request.resources,
                expected_output=(
                    "Proposed corrective actions with supporting rationale "
                    "and evidence."
                ),
                passing_criteria={
                    "agent_status": "SUCCESS",
                },
            ),
            ExecutionStep(
                step_id="step-6",
                objective=(
                    "Prepare the requested approval proposal containing the "
                    "findings, requirements comparison, evidence, and "
                    "proposed corrective actions."
                ),
                dependencies=["step-5"],
                resources=request.resources,
                expected_output=self._get_expected_output(request),
                passing_criteria={
                    "agent_status": "SUCCESS",
                },
            ),
        ]

        return ExecutionPlan(
            request_context=request.request_context,
            task_description=request.user_input,
            executable_steps=steps,
        )

    def _create_single_step_plan(
        self,
        request: TaskRequest,
    ) -> ExecutionPlan:
        """
        Preserve the original first-slice behavior for task types that are
        not yet supported by deterministic decomposition.
        """

        step = ExecutionStep(
            step_id="step-1",
            objective=request.user_input,
            resources=request.resources,
            expected_output=self._get_expected_output(request),
            passing_criteria={
                "agent_status": "SUCCESS",
            },
        )

        return ExecutionPlan(
            request_context=request.request_context,
            task_description=request.user_input,
            executable_steps=[step],
        )

    def _get_expected_output(self, request: TaskRequest) -> str:
        """
        Determine the requested output description for the task.
        """

        if request.requested_output_info:
            return str(request.requested_output_info)

        return "Complete the requested task."