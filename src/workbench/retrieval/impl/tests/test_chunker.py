"""Unit tests for IndustrialDocumentChunker parsing real physical documents."""

import os
from chunker import IndustrialDocumentChunker
from contracts import ResourceType


def test_chunk_real_pdf_document():
    """Verify that chunker extracts text from physical PDF with exact page provenance."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunker = IndustrialDocumentChunker(base_dir)

    chunks = chunker.chunk_pdf(
        rel_path="simulated_mrpl/sops/SOP-CRU-401_v3.2.pdf",
        document_id="DOC-SOP-CRU-401",
        version="v3.2",
        title="CDU Flange Maintenance Specification",
        department="Mechanical Maintenance",
        effective_date="2024-01-15",
        equipment_id="E-204",
    )

    assert len(chunks) >= 1
    top_chunk = chunks[0]
    assert top_chunk.resource_type == ResourceType.TEXT
    assert top_chunk.location.page_number == 1
    assert "SOP-CRU-401" in top_chunk.content or "Flange Torquing" in top_chunk.content
    assert top_chunk.provenance.document_version == "v3.2"


def test_chunk_real_csv_spreadsheet():
    """Verify that chunker converts physical CSV spreadsheet into Markdown table evidence."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunker = IndustrialDocumentChunker(base_dir)

    tables = chunker.chunk_csv_table(
        rel_path="simulated_mrpl/inspection/data/E204_UT_readings.csv",
        document_id="DOC-INSP-E204-2024",
        version="v1.0",
        title="Heat Exchanger E-204 UT Report",
        department="Inspection Dept",
        effective_date="2024-05-18",
        equipment_id="E-204",
    )

    assert len(tables) == 1
    tbl = tables[0]
    assert tbl.resource_type == ResourceType.TABLE
    assert "Nominal Thk" in tbl.content
    assert "E-204 Shell Section A" in tbl.content
    assert tbl.location.sheet_name == "Summary"
