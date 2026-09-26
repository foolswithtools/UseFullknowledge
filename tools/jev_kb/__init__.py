"""TypeSafe Jev client library for UseFullknowledge KB interaction."""
from .models import KnowledgeEntry, SearchResult, CatalogEntry, BatchImportResult
from .client import JevKBClient
__version__ = "0.1.0"
__all__ = ["JevKBClient", "KnowledgeEntry", "SearchResult", "CatalogEntry", "BatchImportResult"]
