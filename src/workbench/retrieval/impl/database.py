"""Simulated MRPL Knowledge Base & Document Repository.

Provides a realistic on-premise industrial repository containing:
- SOPs (Standard Operating Procedures) with active and superseded versions
- Equipment Inspection Reports with multimodal image evidence and bounding boxes
- Equipment Engineering Manuals and specification tables
- Incident Investigation Reports

Matches Person 3 subsystem requirements.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .contracts import (
        LocationReference,
        Provenance,
        ResourceType,
        RetrievedResource,
    )
    from .chunker import IndustrialDocumentChunker
except ImportError:
    from contracts import (
        LocationReference,
        Provenance,
        ResourceType,
        RetrievedResource,
    )
    from chunker import IndustrialDocumentChunker


class SimulatedDocument:
    """Represents an entire document entry in the MRPL registry."""
    def __init__(
        self,
        document_id: str,
        title: str,
        version: str,
        department: str,
        effective_date: str,
        status: str,  # "ACTIVE" or "SUPERSEDED"
        equipment_tags: List[str],
        classification: str = "CONFIDENTIAL_INTERNAL",
    ):
        self.document_id = document_id
        self.title = title
        self.version = version
        self.department = department
        self.effective_date = effective_date
        self.status = status
        self.equipment_tags = equipment_tags
        self.classification = classification


class SimulatedMRPLDatabase:
    """In-memory simulated MRPL repository with automatic directory ingestion."""

    def __init__(self, data_dir: Optional[str] = None, auto_scan: bool = True):
        self.base_dir = Path(__file__).parent.resolve()
        self.data_dir = Path(data_dir).resolve() if data_dir else (self.base_dir / "simulated_mrpl")
        self._documents: Dict[str, List[SimulatedDocument]] = {}
        self._resources: List[RetrievedResource] = []
        self._populate_mrpl_records()
        if auto_scan:
            self.auto_ingest_directory(self.data_dir)

    def _populate_mrpl_records(self):
        """Seeds the database with realistic industrial refinery records."""

        # -------------------------------------------------------------
        # 1. SOP-CRU-401 (Current Version v3.2 - ACTIVE)
        # -------------------------------------------------------------
        doc_sop_v3 = SimulatedDocument(
            document_id="DOC-SOP-CRU-401",
            title="CDU High Pressure Flange Inspection and Torque Procedure",
            version="v3.2",
            department="Mechanical Maintenance & Safety",
            effective_date="2024-01-15",
            status="ACTIVE",
            equipment_tags=["E-204", "CDU-COL-01", "FLANGE-104"],
        )
        self._add_document(doc_sop_v3)

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-sop401-v3-sec4",
                document_id="DOC-SOP-CRU-401",
                document_version="v3.2",
                resource_type=ResourceType.TEXT,
                content=(
                    "Section 4.1 Flange Torquing: Before hot bolting, verify line temperature is below 150°C. "
                    "For ASTM A193 B7 bolts on Heat Exchanger E-204 nozzle flanges, apply cross-pattern torque "
                    "in three stages: 30% (90 Nm), 60% (180 Nm), and final 100% (300 Nm). Always replace spiral-wound "
                    "gaskets with 316L SS inner ring."
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/sops/SOP-CRU-401_v3.2.pdf",
                    page_number=6,
                    section="Section 4.1 Flange Torquing",
                ),
                metadata={
                    "equipment_id": "E-204",
                    "system": "Crude Distillation Unit",
                    "bolt_material": "ASTM A193 B7",
                    "final_torque_nm": 300,
                },
                relevance_score=1.0,
                provenance=Provenance(
                    document_id="DOC-SOP-CRU-401",
                    document_version="v3.2",
                    document_title=doc_sop_v3.title,
                    author_department=doc_sop_v3.department,
                    effective_date=doc_sop_v3.effective_date,
                ),
            )
        )

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-sop401-v3-tbl2",
                document_id="DOC-SOP-CRU-401",
                document_version="v3.2",
                resource_type=ResourceType.TABLE,
                content=(
                    "| Flange Rating | Bolt Size (in) | Stage 1 (Nm) | Stage 2 (Nm) | Final Torque (Nm) |\n"
                    "|---|---|---|---|---|\n"
                    "| Class 300# | 3/4\" | 60 | 120 | 200 |\n"
                    "| Class 600# (E-204) | 7/8\" | 90 | 180 | 300 |\n"
                    "| Class 900# | 1-1/8\" | 150 | 310 | 520 |"
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/sops/SOP-CRU-401_v3.2.pdf",
                    page_number=8,
                    section="Table 2: Standard Torque Matrix",
                ),
                metadata={"equipment_id": "E-204", "table_id": "Table 2", "rating": "Class 600#"},
                relevance_score=1.0,
                provenance=Provenance(
                    document_id="DOC-SOP-CRU-401",
                    document_version="v3.2",
                    document_title=doc_sop_v3.title,
                    author_department=doc_sop_v3.department,
                    effective_date=doc_sop_v3.effective_date,
                ),
            )
        )

        # -------------------------------------------------------------
        # 2. SOP-CRU-401 (Old Version v1.0 - SUPERSEDED)
        # -------------------------------------------------------------
        # Note: In v1.0, the torque was only 220 Nm (an outdated specification).
        doc_sop_v1 = SimulatedDocument(
            document_id="DOC-SOP-CRU-401",
            title="CDU High Pressure Flange Inspection Procedure",
            version="v1.0",
            department="Mechanical Maintenance",
            effective_date="2018-04-10",
            status="SUPERSEDED",
            equipment_tags=["E-204", "CDU-COL-01"],
        )
        self._add_document(doc_sop_v1)

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-sop401-v1-sec3",
                document_id="DOC-SOP-CRU-401",
                document_version="v1.0",
                resource_type=ResourceType.TEXT,
                content=(
                    "[SUPERSEDED] Section 3.0: E-204 flange torque requirement: Tighten bolts to 220 Nm. "
                    "Asbestos-filled gaskets may be reused if undamaged."
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/sops/archived/SOP-CRU-401_v1.0.pdf",
                    page_number=4,
                    section="Section 3.0",
                ),
                metadata={"equipment_id": "E-204", "status": "SUPERSEDED"},
                relevance_score=0.8,
                provenance=Provenance(
                    document_id="DOC-SOP-CRU-401",
                    document_version="v1.0",
                    document_title=doc_sop_v1.title,
                    author_department=doc_sop_v1.department,
                    effective_date=doc_sop_v1.effective_date,
                ),
            )
        )

        # -------------------------------------------------------------
        # 3. DOC-INSP-E204-2024 (Inspection Report with Visual Photo)
        # -------------------------------------------------------------
        doc_insp = SimulatedDocument(
            document_id="DOC-INSP-E204-2024",
            title="Heat Exchanger E-204 Annual Ultrasonic & Visual Integrity Report",
            version="v1.0",
            department="Asset Integrity & Inspection",
            effective_date="2024-05-18",
            status="ACTIVE",
            equipment_tags=["E-204"],
        )
        self._add_document(doc_insp)

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-insp-e204-img1",
                document_id="DOC-INSP-E204-2024",
                document_version="v1.0",
                resource_type=ResourceType.IMAGE,
                content=(
                    "Photograph: Flange F-104 North nozzle weld showing localized crevice corrosion and pitting. "
                    "Measured pit depth: 2.1 mm. Requires weld overlay repair before next turnaround."
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/inspection/photos/E204_flange_corrosion_pit.png",
                    page_number=12,
                    bounding_box=[150.0, 200.0, 480.0, 620.0],
                ),
                metadata={
                    "equipment_id": "E-204",
                    "inspection_method": "Visual + Pit Gauge",
                    "defect_depth_mm": 2.1,
                    "severity": "CRITICAL",
                },
                relevance_score=1.0,
                provenance=Provenance(
                    document_id="DOC-INSP-E204-2024",
                    document_version="v1.0",
                    document_title=doc_insp.title,
                    author_department=doc_insp.department,
                    effective_date=doc_insp.effective_date,
                ),
            )
        )

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-insp-e204-tbl-ut",
                document_id="DOC-INSP-E204-2024",
                document_version="v1.0",
                resource_type=ResourceType.TABLE,
                content=(
                    "| Location Tag | Nominal Thk (mm) | Measured Thk (mm) | Min Allowable (mm) | Status |\n"
                    "|---|---|---|---|---|\n"
                    "| E-204 Shell Section A | 16.0 | 14.8 | 12.5 | ACCEPTABLE |\n"
                    "| E-204 Nozzle N1 | 12.5 | 9.4 | 9.0 | ALERT |\n"
                    "| E-204 Channel Head | 18.0 | 17.2 | 14.0 | ACCEPTABLE |"
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/inspection/data/E204_UT_readings.csv",
                    sheet_name="UT_Thickness_Summary",
                    row_range=[1, 5],
                ),
                metadata={"equipment_id": "E-204", "technique": "Ultrasonic Testing (UT)"},
                relevance_score=1.0,
                provenance=Provenance(
                    document_id="DOC-INSP-E204-2024",
                    document_version="v1.0",
                    document_title=doc_insp.title,
                    author_department=doc_insp.department,
                    effective_date=doc_insp.effective_date,
                ),
            )
        )

        # -------------------------------------------------------------
        # 4. DOC-MAN-P101A (Equipment Manual)
        # -------------------------------------------------------------
        doc_pump = SimulatedDocument(
            document_id="DOC-MAN-P101A",
            title="Heavy Crude Charge Pump P-101A Technical Manual & Seal Plan",
            version="v2.0",
            department="Vendor OEM - Sulzer Pumps",
            effective_date="2022-09-01",
            status="ACTIVE",
            equipment_tags=["P-101A"],
        )
        self._add_document(doc_pump)

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-pump101-p32",
                document_id="DOC-MAN-P101A",
                document_version="v2.0",
                resource_type=ResourceType.TEXT,
                content=(
                    "P-101A Mechanical Seal: Dual pressurized cartridge seal operating per API Plan 53B. "
                    "Barrier fluid accumulator bladder pre-charge pressure: 12.0 bar at 20°C. "
                    "Maximum allowable shaft vibration during operation is 3.5 mm/s RMS."
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/manuals/P101A_OEM_Manual.pdf",
                    page_number=32,
                    section="Chapter 5: Mechanical Seals",
                ),
                metadata={"equipment_id": "P-101A", "seal_plan": "API Plan 53B", "vibration_limit_rms": 3.5},
                relevance_score=1.0,
                provenance=Provenance(
                    document_id="DOC-MAN-P101A",
                    document_version="v2.0",
                    document_title=doc_pump.title,
                    author_department=doc_pump.department,
                    effective_date=doc_pump.effective_date,
                ),
            )
        )

        # -------------------------------------------------------------
        # 5. DOC-INC-2023-09 (Incident Investigation Report)
        # -------------------------------------------------------------
        doc_inc = SimulatedDocument(
            document_id="DOC-INC-2023-09",
            title="Root Cause Analysis: Hydrocarbon Gas Leak from Flange F-104",
            version="v1.0",
            department="Process Safety & HSE",
            effective_date="2023-10-05",
            status="ACTIVE",
            equipment_tags=["FLANGE-104", "E-204", "CDU-COL-01"],
        )
        self._add_document(doc_inc)

        self._resources.append(
            RetrievedResource(
                evidence_id="ev-inc-2023-rca",
                document_id="DOC-INC-2023-09",
                document_version="v1.0",
                resource_type=ResourceType.TEXT,
                content=(
                    "Incident Summary: On 2023-09-14, a pinhole leak was detected at Flange F-104 on the inlet of E-204. "
                    "Root Cause: Maintenance personnel utilized obsolete torque specifications from SOP-CRU-401 v1.0 (220 Nm "
                    "instead of 300 Nm required by v3.2), leading to uneven gasket relaxation during thermal cycling. "
                    "Corrective Action: Mandatory verification of current SOP revision in workbench before issuing work permits."
                ),
                location=LocationReference(
                    file_path="simulated_mrpl/incidents/INC-2023-09-F104_Leak_RCA.pdf",
                    page_number=2,
                    section="Executive Summary & Findings",
                ),
                metadata={"equipment_id": "E-204", "incident_date": "2023-09-14", "severity": "HIGH"},
                relevance_score=1.0,
                provenance=Provenance(
                    document_id="DOC-INC-2023-09",
                    document_version="v1.0",
                    document_title=doc_inc.title,
                    author_department=doc_inc.department,
                    effective_date=doc_inc.effective_date,
                ),
            )
        )

    def _add_document(self, doc: SimulatedDocument):
        if doc.document_id not in self._documents:
            self._documents[doc.document_id] = []
        self._documents[doc.document_id].append(doc)

    def get_document_versions(self, document_id: str) -> List[SimulatedDocument]:
        """Returns all versions of a document."""
        return self._documents.get(document_id, [])

    def get_active_version(self, document_id: str) -> Optional[SimulatedDocument]:
        """Finds the current ACTIVE version of a document."""
        for doc in self._documents.get(document_id, []):
            if doc.status == "ACTIVE":
                return doc
        return None

    def list_all_resources(self) -> List[RetrievedResource]:
        """Returns all indexed multimodal resources."""
        return self._resources

    def get_document_status(self, document_id: str, version: str) -> Optional[str]:
        """Checks if a specific document version is ACTIVE or SUPERSEDED."""
        for doc in self._documents.get(document_id, []):
            if doc.version == version:
                return doc.status
        return None

    def get_absolute_path(self, rel_or_abs_path: str) -> str:
        """Returns the absolute file path, anchored to the retrieval subsystem directory."""
        if os.path.isabs(rel_or_abs_path):
            return rel_or_abs_path
        return str((self.base_dir / rel_or_abs_path).resolve())

    def auto_ingest_directory(self, target_dir: Optional[Path] = None):
        """Automatically scans for any unindexed files and ingests them into the knowledge base."""
        target_dir = Path(target_dir) if target_dir else self.data_dir
        if not target_dir.exists():
            return

        chunker = IndustrialDocumentChunker(base_data_dir=str(self.base_dir))
        indexed_paths = {
            os.path.normpath(res.location.file_path)
            for res in self._resources
            if res.location and res.location.file_path
        }

        for root, _, files in os.walk(target_dir):
            for file in sorted(files):
                full_file_path = Path(root) / file
                rel_path = os.path.relpath(full_file_path, self.base_dir).replace("\\", "/")
                norm_rel = os.path.normpath(rel_path)

                if norm_rel in indexed_paths:
                    continue  # Already indexed in pre-populated catalog

                ext = file.lower().split(".")[-1]
                doc_name = file.rsplit(".", 1)[0]

                # Parse version if present (e.g. SOP-CRU-500_v2.1 -> v2.1)
                version = "v1.0"
                if "_v" in doc_name:
                    parts = doc_name.split("_v")
                    version = "v" + parts[-1]

                status = "ACTIVE"
                if "archived" in root.lower() or "superseded" in root.lower():
                    status = "SUPERSEDED"

                doc_id = f"DOC-{doc_name.upper()}"
                sim_doc = SimulatedDocument(
                    document_id=doc_id,
                    title=f"Auto-Ingested: {doc_name}",
                    version=version,
                    department="Plant Operations",
                    effective_date="2024-01-01",
                    status=status,
                    equipment_tags=[],
                )
                self._add_document(sim_doc)

                if ext == "pdf":
                    try:
                        chunks = chunker.chunk_pdf(
                            rel_path=rel_path,
                            document_id=doc_id,
                            version=version,
                            title=sim_doc.title,
                            department=sim_doc.department,
                            effective_date=sim_doc.effective_date,
                        )
                        self._resources.extend(chunks)
                        indexed_paths.add(norm_rel)
                    except Exception:
                        pass
                elif ext == "csv":
                    try:
                        chunks = chunker.chunk_csv_table(
                            rel_path=rel_path,
                            document_id=doc_id,
                            version=version,
                            title=sim_doc.title,
                            department=sim_doc.department,
                            effective_date=sim_doc.effective_date,
                            sheet_name=doc_name,
                        )
                        self._resources.extend(chunks)
                        indexed_paths.add(norm_rel)
                    except Exception:
                        pass
                elif ext in ("png", "jpg", "jpeg"):
                    img_res = RetrievedResource(
                        evidence_id=f"ev-img-{doc_name.lower()}",
                        document_id=doc_id,
                        document_version=version,
                        resource_type=ResourceType.IMAGE,
                        content=f"Visual asset: {file}",
                        location=LocationReference(
                            file_path=rel_path,
                        ),
                        metadata={"format": ext.upper()},
                        relevance_score=1.0,
                        provenance=Provenance(
                            document_id=doc_id,
                            document_version=version,
                            document_title=sim_doc.title,
                            author_department=sim_doc.department,
                            effective_date=sim_doc.effective_date,
                        ),
                    )
                    self._resources.append(img_res)
                    indexed_paths.add(norm_rel)

