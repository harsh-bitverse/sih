"""Industrial Document Ingestion & Contextual Chunker with Full Provenance.

Parses real physical documents from disk:
- Digital PDFs via pypdf (extracts page-by-page text)
- Tabular CSV spreadsheets (extracts structured rows)
- Visual image assets (records bounding-box coordinates)

Constructs standardized RetrievedResource chunks where every chunk
carries its exact provenance passport (Slide 12: Evidence Contract).
"""

import os
from typing import List, Optional
from pypdf import PdfReader
try:
    from .contracts import (
        LocationReference,
        Provenance,
        ResourceType,
        RetrievedResource,
    )
except ImportError:
    from contracts import (
        LocationReference,
        Provenance,
        ResourceType,
        RetrievedResource,
    )


class IndustrialDocumentChunker:
    """Parses real physical refinery files and chunks them with provenance preservation."""

    def __init__(self, base_data_dir: str):
        self.base_data_dir = os.path.abspath(base_data_dir)

    def chunk_pdf(
        self,
        rel_path: str,
        document_id: str,
        version: str,
        title: str,
        department: str,
        effective_date: str,
        equipment_id: Optional[str] = None,
        max_chunk_chars: int = 500,
    ) -> List[RetrievedResource]:
        """Extracts text from a real PDF file page-by-page, chunking with section/page provenance."""
        full_path = rel_path if os.path.isabs(rel_path) else os.path.join(self.base_data_dir, rel_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"PDF file not found: {full_path}")

        reader = PdfReader(full_path)
        resources: List[RetrievedResource] = []

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            # Split page into meaningful paragraphs/sections
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

            for chunk_idx, para in enumerate(paragraphs, start=1):
                # Clean up single linebreaks within a paragraph
                clean_content = " ".join(para.split())
                if len(clean_content) < 15:
                    continue  # skip empty/tiny artifacts

                evidence_id = f"ev-{document_id}-p{page_idx}-c{chunk_idx}"

                # Extract likely heading if paragraph starts with Section
                section_name = None
                if "Section" in clean_content[:30]:
                    section_name = clean_content.split(":")[0]

                res = RetrievedResource(
                    evidence_id=evidence_id,
                    document_id=document_id,
                    document_version=version,
                    resource_type=ResourceType.TEXT,
                    content=clean_content,
                    location=LocationReference(
                        file_path=rel_path.replace("\\", "/"),
                        page_number=page_idx,
                        section=section_name,
                    ),
                    metadata={
                        "equipment_id": equipment_id,
                        "source_format": "PDF",
                        "page_number": page_idx,
                    },
                    relevance_score=1.0,
                    provenance=Provenance(
                        document_id=document_id,
                        document_version=version,
                        document_title=title,
                        author_department=department,
                        effective_date=effective_date,
                    ),
                )
                resources.append(res)

        return resources

    def chunk_csv_table(
        self,
        rel_path: str,
        document_id: str,
        version: str,
        title: str,
        department: str,
        effective_date: str,
        equipment_id: Optional[str] = None,
        sheet_name: Optional[str] = "Summary",
    ) -> List[RetrievedResource]:
        """Parses a real CSV spreadsheet into structured Markdown table evidence."""
        full_path = rel_path if os.path.isabs(rel_path) else os.path.join(self.base_data_dir, rel_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"CSV file not found: {full_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            return []

        # Convert CSV rows to clean Markdown table
        headers = [h.strip() for h in lines[0].split(",")]
        md_table = "| " + " | ".join(headers) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        for row_str in lines[1:]:
            cols = [c.strip() for c in row_str.split(",")]
            md_table += "| " + " | ".join(cols) + " |\n"

        res = RetrievedResource(
            evidence_id=f"ev-{document_id}-tbl-summary",
            document_id=document_id,
            document_version=version,
            resource_type=ResourceType.TABLE,
            content=md_table.strip(),
            location=LocationReference(
                file_path=rel_path.replace("\\", "/"),
                sheet_name="Summary",
                row_range=[1, len(lines)],
            ),
            metadata={
                "equipment_id": equipment_id,
                "total_rows": len(lines) - 1,
                "columns": headers,
            },
            relevance_score=1.0,
            provenance=Provenance(
                document_id=document_id,
                document_version=version,
                document_title=title,
                author_department=department,
                effective_date=effective_date,
            ),
        )
        return [res]
