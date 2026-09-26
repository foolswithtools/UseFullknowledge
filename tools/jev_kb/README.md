# TypeSafe Jev Client Library

A thin Pydantic-typed wrapper around the existing `kbtool` CLI, providing structured, type-checked calls for agents consuming the knowledge base.

## Installation

```bash
pip install pydantic pyyaml
```

## Usage

```python
from jev_kb import JevKBClient, KnowledgeEntry

client = JevKBClient(repo_root="/path/to/UseFullknowledge")

# Search by tag
results = client.search(tag="trading")
for r in results:
    print(r.title, r.review_status)

# Get a single document
entry = client.get("complexity-rarely-adds-value-5e01")
print(entry.title, entry.body[:200])

# Create a new document scaffold
msg = client.create("explainer", "New Topic", tool="loup", model="claude")

# Update frontmatter
client.update("doc-id-1234", {"review_status": "verified"}, reviewer="clo", reviewer_kind="human")

# Export all KB documents as JSONL
jsonl = client.export_jsonl()

# Import documents from JSONL (validates via Pydantic)
result = client.import_jsonl(jsonl_string)
print(f"Imported: {result.imported}, Failed: {result.failed}")

# List only verified documents
verified = client.list_verified()

# Run KB validation check
report = client.check()
print(report["valid"], report["errors"])
```

## Models

- `KnowledgeEntry` — full document with frontmatter + body
- `SearchResult` — lightweight search hit
- `CatalogEntry` — published site catalog entry
- `BatchImportResult` — import operation result

All models validate via Pydantic, catching schema violations at call time.
