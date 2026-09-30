"""Generates physical sample files (real valid PNG, PDF, and CSV files)
for the simulated MRPL repository.

Runs with pure Python standard library (no extra dependencies required).
"""

import os
import struct
import zlib


def create_minimal_png(file_path: str, width: int = 400, height: int = 300):
    """Creates a genuine, valid PNG image with simulated corrosion pit pixels."""
    # Raw RGB pixel data (grey background with a rust-orange spot in the center)
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # Filter byte: None
        for x in range(width):
            # If inside the simulated corrosion pit area (center)
            if 150 <= x <= 250 and 100 <= y <= 200:
                raw_data.extend([180, 70, 30])  # Rust orange/brown
            else:
                raw_data.extend([200, 205, 210])  # Steel grey

    compressed = zlib.compress(bytes(raw_data))

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + chunk + crc

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # PNG Signature
        + make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + make_chunk(b"IDAT", compressed)
        + make_chunk(b"IEND", b"")
    )

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(png_bytes)


def create_minimal_pdf(file_path: str, title: str, text_lines: list):
    """Creates a genuine, valid PDF 1.4 file containing printable text."""
    content_stream = "BT /F1 12 Tf 50 750 Td 15 TL\n"
    content_stream += f"({title}) Tj T*\nT*\n"
    for line in text_lines:
        safe_line = line.replace("(", "\\(").replace(")", "\\)")
        content_stream += f"({safe_line}) Tj T*\n"
    content_stream += "ET"

    stream_bytes = content_stream.encode("latin-1")
    length = len(stream_bytes)

    objects = [
        b"%PDF-1.4\n",
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {length} >>\nstream\n".encode("latin-1") + stream_bytes + b"\nendstream\nendobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        offsets = []
        pos = 0
        for obj in objects:
            offsets.append(pos)
            f.write(obj)
            pos += len(obj)

        xref_pos = pos
        f.write(f"xref\n0 {len(objects)}\n0000000000 65535 f \n".encode("latin-1"))
        for off in offsets[1:]:
            f.write(f"{off:010d} 00000 n \n".encode("latin-1"))
        f.write(f"trailer << /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1"))


def create_sample_csv(file_path: str, rows: list):
    """Creates an inspection table spreadsheet file (CSV format)."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(",".join(r) + "\n")


def generate_all_files(base_dir: str):
    """Generates all physical files required by the simulated database."""
    # 1. SOP v3.2 PDF
    create_minimal_pdf(
        os.path.join(base_dir, "sops", "SOP-CRU-401_v3.2.pdf"),
        "MRPL - SOP-CRU-401 (Revision v3.2) - ACTIVE",
        [
            "CRUDE DISTILLATION UNIT FLANGE MAINTENANCE SPECIFICATION",
            "Effective Date: 2024-01-15 | Department: Mechanical Maintenance",
            "",
            "Section 4.1 Flange Torquing:",
            "Before hot bolting, verify line temperature is below 150 deg C.",
            "For ASTM A193 B7 bolts on Heat Exchanger E-204 nozzle flanges,",
            "apply cross-pattern torque in three stages:",
            "Stage 1: 30% (90 Nm)",
            "Stage 2: 60% (180 Nm)",
            "Stage 3: 100% final (300 Nm).",
            "Always replace spiral-wound gaskets with 316L SS inner ring.",
        ],
    )

    # 2. SOP v1.0 PDF (Archived)
    create_minimal_pdf(
        os.path.join(base_dir, "sops", "archived", "SOP-CRU-401_v1.0.pdf"),
        "MRPL - SOP-CRU-401 (Revision v1.0) - [SUPERSEDED - DO NOT USE]",
        [
            "ARCHIVED FLANGE MAINTENANCE PROCEDURE (SUPERSEDED 2021)",
            "Section 3.0: E-204 flange torque requirement: Tighten bolts to 220 Nm.",
            "Asbestos-filled gaskets may be reused if undamaged.",
        ],
    )

    # 3. Corrosion Photo (Real PNG)
    create_minimal_png(
        os.path.join(base_dir, "inspection", "photos", "E204_flange_corrosion_pit.png"),
        width=400,
        height=300,
    )

    # 4. UT Thickness Table (CSV)
    create_sample_csv(
        os.path.join(base_dir, "inspection", "data", "E204_UT_readings.csv"),
        [
            ["Location Tag", "Nominal Thk (mm)", "Measured Thk (mm)", "Min Allowable (mm)", "Status"],
            ["E-204 Shell Section A", "16.0", "14.8", "12.5", "ACCEPTABLE"],
            ["E-204 Nozzle N1", "12.5", "9.4", "9.0", "ALERT"],
            ["E-204 Channel Head", "18.0", "17.2", "14.0", "ACCEPTABLE"],
        ],
    )

    # 5. OEM Pump Manual PDF
    create_minimal_pdf(
        os.path.join(base_dir, "manuals", "P101A_OEM_Manual.pdf"),
        "OEM VENDOR MANUAL - Heavy Crude Charge Pump P-101A",
        [
            "Manufacturer: Sulzer Pumps | Model: 6x8x13 CAP-B",
            "Mechanical Seal: Dual pressurized cartridge seal operating per API Plan 53B.",
            "Barrier fluid accumulator bladder pre-charge pressure: 12.0 bar at 20 deg C.",
            "Maximum allowable shaft vibration during operation is 3.5 mm/s RMS.",
        ],
    )

    # 6. Incident Investigation PDF
    create_minimal_pdf(
        os.path.join(base_dir, "incidents", "INC-2023-09-F104_Leak_RCA.pdf"),
        "MRPL INCIDENT REPORT - INC-2023-09 (Flange F-104 Gas Leak)",
        [
            "Date of Incident: 2023-09-14 | Severity: HIGH | Classification: CONFIDENTIAL",
            "Root Cause Summary:",
            "Maintenance crew used obsolete torque specifications from SOP-CRU-401 v1.0",
            "(220 Nm instead of 300 Nm required by current v3.2).",
            "Corrective Action: AI Workbench must enforce version policy before permit release.",
        ],
    )


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(current_dir, "simulated_mrpl")
    generate_all_files(target_dir)
    print(f"Successfully generated physical MRPL documents in: {target_dir}")
