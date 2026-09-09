"""
Planner Subsystem Interface.

Owned by: Developer 1 (System Architect)
Subsystem: planner

The Planner directly decomposes a TaskRequest into meaningful executable steps (ExecutionPlan).
There is NO separate Orchestrator in the MVP.
"""

from workbench.planner.schemas import ExecutionPlan, TaskRequest


class Planner:
    """
    Decomposes incoming TaskRequests into executable ExecutionPlans.
    """

    def create_plan(self, request: TaskRequest) -> ExecutionPlan:
        """
        Decomposes a TaskRequest into executable steps with passing criteria and dependencies.
        """
        raise NotImplementedError("Planner.create_plan will be implemented by Developer 1.")
