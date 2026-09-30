"""Unit tests for Simulated MRPL Database."""

from database import SimulatedMRPLDatabase
from contracts import ResourceType


def test_database_initialization():
    """Verify that simulated MRPL documents and multimodal resources load correctly."""
    db = SimulatedMRPLDatabase()
    resources = db.list_all_resources()
    assert len(resources) >= 6

    # Verify distinct document types exist
    doc_ids = {r.document_id for r in resources}
    assert "DOC-SOP-CRU-401" in doc_ids
    assert "DOC-INSP-E204-2024" in doc_ids
    assert "DOC-MAN-P101A" in doc_ids
    assert "DOC-INC-2023-09" in doc_ids


def test_document_versioning_tracking():
    """Verify that SOP-CRU-401 has both active and superseded versions."""
    db = SimulatedMRPLDatabase()

    versions = db.get_document_versions("DOC-SOP-CRU-401")
    assert len(versions) == 2

    # Check statuses
    status_map = {doc.version: doc.status for doc in versions}
    assert status_map["v3.2"] == "ACTIVE"
    assert status_map["v1.0"] == "SUPERSEDED"

    # Active version lookup
    active_doc = db.get_active_version("DOC-SOP-CRU-401")
    assert active_doc is not None
    assert active_doc.version == "v3.2"


def test_multimodal_resources_structure():
    """Verify that image with bounding box and table with rows exist in the DB."""
    db = SimulatedMRPLDatabase()
    resources = db.list_all_resources()

    # Find the inspection image
    images = [r for r in resources if r.resource_type == ResourceType.IMAGE]
    assert len(images) >= 1
    insp_img = images[0]
    assert insp_img.location.bounding_box == [150.0, 200.0, 480.0, 620.0]
    assert insp_img.location.page_number == 12
    assert insp_img.metadata["severity"] == "CRITICAL"

    # Find tables
    tables = [r for r in resources if r.resource_type == ResourceType.TABLE]
    assert len(tables) >= 2
    ut_table = [t for t in tables if "UT_Thickness_Summary" in str(t.location.sheet_name)][0]
    assert ut_table.location.sheet_name == "UT_Thickness_Summary"
    assert "Nominal Thk" in ut_table.content


def test_physical_files_exist_on_disk():
    """Verify that every resource points to an actual physical file on disk."""
    import os
    db = SimulatedMRPLDatabase()
    resources = db.list_all_resources()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for res in resources:
        full_path = os.path.join(base_dir, res.location.file_path)
        assert os.path.exists(full_path), f"Physical file missing for evidence {res.evidence_id}: {full_path}"


def test_auto_ingest_new_file(tmp_path):
    """Verify that dropping a new CSV or file is automatically ingested without code changes."""
    test_csv = tmp_path / "NEW_PUMP_TEST.csv"
    test_csv.write_text("Equipment,Parameter,Value\nPUMP-999,FlowRate,500m3/h\n")

    db = SimulatedMRPLDatabase(data_dir=str(tmp_path), auto_scan=False)
    initial_count = len(db.list_all_resources())

    db.auto_ingest_directory(target_dir=tmp_path)
    new_resources = db.list_all_resources()

    assert len(new_resources) > initial_count
    matching = [r for r in new_resources if "PUMP-999" in r.content]
    assert len(matching) >= 1

