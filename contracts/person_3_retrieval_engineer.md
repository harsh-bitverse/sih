# PERSON 3 — RETRIEVAL ENGINEER

## Final-system ownership

Own:

- company knowledge ingestion
- indexing
- retrieval
- document registry
- versioning
- metadata
- hybrid search
- provenance
- permissions-aware retrieval

## MVP subsystem

```text
Sample MRPL Knowledge Base
        ↓
ingestion
        ↓
index
        ↓
retrieval API
```

## Actually build now

Use a small simulated MRPL database containing:

- SOPs
- manuals
- incident reports
- inspection reports
- equipment information
- historical records

Implement:

```text
query
    ↓
relevant documents
    ↓
relevant passages/resources
    ↓
metadata/provenance
```

Don't build enterprise-grade ingestion.

## 4. Retrieval subsystem

Person 3 owns this.

The rest of the system shouldn't know how the documents are indexed.

### Input: `RetrievalRequest`

```text
RetrievalRequest
├── request_context
├── query
├── source_scope
├── filters?
├── version_policy
├── modality_filter?
├── max_results?
└── required_information
```

### Example

```text
query:
    "Current SOP requirements for corrosion
    inspection of E-204"

source_scope:
    "MRPL safety documentation"

version_policy:
    "current_only"

required_information:
    "Relevant requirements and source references"
```

### Output: `RetrievalResult`

```text
RetrievalResult
├── request_context
├── status
├── results[]
└── errors[]
```

Each result:

```text
RetrievedResource
├── evidence_id
├── document_id
├── document_version
├── resource_type
├── content/reference
├── location
├── metadata
├── relevance
└── provenance
```

### Important

`content/reference` might be:

```text
text
PDF
image
table
document
file reference
```

Retrieval doesn't need to understand the content deeply.

Its job is:

> Find the relevant source material and preserve where it came from.
