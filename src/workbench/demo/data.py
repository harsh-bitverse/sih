"""
Synthetic MRPL Demo Data for Equipment E-204 Inspection & Corrective Action.

Owned by: Developer 1 (System Architect)
Subsystem: demo

Provides realistic industrial data models and TaskRequests for equipment E-204.
"""

from typing import List
from uuid import uuid4

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference, ResourceType
from workbench.planner.schemas import TaskRequest

E204_TASK_PROMPT = (
    "Analyze the attached inspection/incident package for equipment E-204. "
    "Identify safety findings, determine applicable SOP requirements, "
    "compare with previous incidents, recommend corrective actions, "
    "and prepare a corrective action plan."
)


def create_mrpl_e204_resources() -> List[ResourceReference]:
    """
    Creates synthetic MRPL resource references for Equipment E-204.
    """
    return [
        ResourceReference(
            resource_id="res-e204-inspection-report",
            resource_type=ResourceType.USER_PROVIDED,
            uri_or_path="data/demo/inspection_report_e204.pdf",
            provenance={
                "source": "on_premise_intake",
                "author": "Field Inspector A. Sharma",
                "facility": "Refinery Unit 4",
                "equipment_id": "E-204",
                "date": "2026-09-28",
            },
            metadata={
                "title": "Equipment E-204 Quarterly Inspection Report",
                "finding_summary": "Bearing vibration 3.8 mm/s RMS (exceeding 2.5 mm/s limit), primary seal oil seepage.",
            },
        ),
        ResourceReference(
            resource_id="res-e204-casing-photo",
            resource_type=ResourceType.USER_PROVIDED,
            uri_or_path="data/demo/equipment_photo_e204.png",
            provenance={
                "source": "thermal_camera_casing_inspection",
                "timestamp": "2026-09-28T10:15:00Z",
                "sensor_model": "FLIR T1020",
                "multimodal": True,
            },
            metadata={
                "title": "Drive-End Bearing Casing Thermal Imaging",
                "thermal_anomaly": "Surface temperature 92°C near drive end bearing housing.",
            },
        ),
        ResourceReference(
            resource_id="res-e204-safety-sop",
            resource_type=ResourceType.RETRIEVED,
            uri_or_path="data/demo/safety_SOP_eng204.pdf",
            provenance={
                "source": "sovereign_rag_kb",
                "sop_id": "SOP-ENG-204",
                "revision": "v3.1",
            },
            metadata={
                "title": "SOP-ENG-204: Industrial Centrifugal Pump Safety & Maintenance Standard",
                "max_vibration_rms": "2.5 mm/s",
                "max_seal_temp": "85.0°C",
            },
        ),
        ResourceReference(
            resource_id="res-e204-incident-17",
            resource_type=ResourceType.RETRIEVED,
            uri_or_path="data/demo/previous_incident_17.pdf",
            provenance={
                "source": "incident_database",
                "incident_id": "INC-2023-017",
                "year": 2023,
            },
            metadata={
                "title": "Incident Report #17: E-204 Bearing Failure & Thermal Runaway",
                "root_cause": "Unaddressed bearing vibration led to mechanical seal disintegration.",
            },
        ),
    ]


def create_mrpl_e204_task_request(
    task_id: str = "task-mrpl-e204-001",
    user_id: str = "plant_safety_lead",
) -> TaskRequest:
    """
    Constructs a validated TaskRequest for the Equipment E-204 inspection scenario.
    """
    context = RequestContext(
        request_id=f"req-{uuid4()}",
        task_id=task_id,
        user_id=user_id,
        source_component="mrpl_demo_intake",
    )
    resources = create_mrpl_e204_resources()
    requested_output_info = {
        "format": "pdf",
        "title": "Corrective Action Plan - Equipment E-204",
        "description": "Comprehensive inspection analysis, SOP gap analysis, historical incident correlation, and prioritized corrective actions for E-204.",
    }

    return TaskRequest(
        request_context=context,
        user_input=E204_TASK_PROMPT,
        resources=resources,
        requested_output_info=requested_output_info,
    )
