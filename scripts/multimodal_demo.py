"""
Manual demo for the multimodal subsystem.

Owned by: Developer 4 (Multimodal Engineer)

    python scripts/multimodal_demo.py <file.pdf|file.png>
    python scripts/multimodal_demo.py <file> --json
    python scripts/multimodal_demo.py <file> --audit

--audit walks one evidence item back to the stored page image, which is the
traceability claim this subsystem exists to support.
"""

import argparse
import logging
import sys
from pathlib import Path

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference, ResourceType
from workbench.multimodal.adapters.local_artifact_store import LocalArtifactStore
from workbench.multimodal.adapters.path_resource_resolver import PathResourceResolver
from workbench.multimodal.adapters.tesseract_backend import TesseractOcrBackend
from workbench.multimodal.processor import DefaultMultimodalProcessor
from workbench.multimodal.schemas import MultimodalRequest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="PDF or image to process")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--artifacts", default="outputs/multimodal_artifacts")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    source = Path(args.path).resolve()
    if not source.is_file():
        print(f"No such file: {source}", file=sys.stderr)
        return 1

    # The resolver is a security boundary: only this directory is readable.
    resolver = PathResourceResolver(allowed_roots=[source.parent])
    store = LocalArtifactStore(args.artifacts)
    processor = DefaultMultimodalProcessor(
        TesseractOcrBackend(), resolver, store, dpi=args.dpi
    )

    result = processor.process(
        MultimodalRequest(
            request_context=RequestContext(
                request_id="req-demo",
                task_id="task-demo",
                user_id="demo-user",
                step_id="step-1",
                source_component="multimodal_demo",
            ),
            resource=ResourceReference(
                resource_id="res_demo",
                resource_type=ResourceType.USER_PROVIDED,
                uri_or_path=str(source),
            ),
            modalities=["ocr"],
        )
    )

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    if args.audit:
        if not result.evidence:
            print("No evidence produced.")
            return 1
        item = result.evidence[0]
        image = store.get(item.source_artifact)
        print("Evidence   :", item.evidence_id)
        print("Content    :", item.content)
        print("Location   :", item.location)
        print("Artifact   :", item.source_artifact,
              f"({len(image)} bytes retrieved)")
        print("Region     :", item.provenance["region"])
        print("Document   :", item.provenance["document_hash"][:16], "...")
        print("Extractor  :", item.provenance["extractor"])
        print("Confidence :", item.confidence, "via", item.confidence_source.value)
        return 0

    print(f"status: {result.status.value}")
    for item in result.evidence:
        region = item.provenance.get("region", {})
        print(
            f"[p{item.provenance['page_index']} "
            f"({region.get('x0', 0):.3f},{region.get('y0', 0):.3f})-"
            f"({region.get('x1', 0):.3f},{region.get('y1', 0):.3f}) "
            f"conf={item.confidence:.2f} {item.confidence_source.value}] "
            f"{item.content}"
        )
    for error in result.errors:
        print("ERROR:", error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
