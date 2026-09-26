"""TypeSafe metadata enrichment for KB entries.

Standardizes entry metadata using Jev-defined schemas to improve
retrieval relevance and downstream reasoning quality.

Usage:
    from jev_kb.enrichment import MetadataEnricher
    enricher = MetadataEnricher(repo_root=".")
    enricher.enrich_entry("complexity-rarely-adds-value-5e01", {
        "confidence_basis": ["empirical", "backtested-10x"],
        "volatility": "slow",
    })
"""
from __future__ import annotations
import pathlib
import yaml
from typing import Optional, List, Dict, Any
from .models import KnowledgeEntry


# Jev-defined volatility taxonomy
VOLATILITY_LEVELS = {
    "fast": "Changes within days/weeks (e.g., market data, API responses)",
    "medium": "Changes within months (e.g., regulatory rules, tool versions)",
    "slow": "Changes within years (e.g., architectural patterns, mental models)",
    "glacial": "Rarely changes (e.g., mathematical proofs, physical constants)",
}

# Jev-defined confidence basis taxonomy
CONFIDENCE_BASIS_TYPES = {
    "empirical": "Validated against real-world data or experiments",
    "backtested": "Tested against historical data with quantified results",
    "theoretical": "Derived from established theory or framework",
    "expert": "Based on expert judgment or domain knowledge",
    "consensus": "Aligned with multiple independent sources",
    "inferred": "Logically derived from other known facts",
    "unverified": "Not yet validated against external sources",
}

# Jev-defined review status taxonomy
REVIEW_STATUSES = {
    "unreviewed": "Entry has not been reviewed by a human",
    "verified": "Entry has been reviewed and confirmed accurate by a human",
    "rejected": "Entry has been reviewed and found inaccurate or outdated",
    "superseded": "Entry has been replaced by a newer version",
}

# Jev-defined entry type taxonomy
ENTRY_TYPES = {
    "explainer": "Detailed explanation of a concept or mechanism",
    "diagram": "Visual representation of architecture or relationships",
    "snippet": "Reusable code or configuration pattern",
    "prompt": "Prompt template for LLM interaction",
    "note": "Observation or insight worth preserving",
}


class MetadataEnricher:
    """Enriches KB entries with standardized metadata fields."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = pathlib.Path(repo_root)

    def enrich_entry(self, doc_id: str, metadata: Dict[str, Any]) -> str:
        """Add or update metadata fields on an existing KB entry.
        
        Args:
            doc_id: The document ID (e.g., "complexity-rarely-adds-value-5e01")
            metadata: Dict of fields to update. Supported keys:
                - confidence_basis: List[str] from CONFIDENCE_BASIS_TYPES
                - volatility: str from VOLATILITY_LEVELS
                - review_status: str from REVIEW_STATUSES
                - review_reviewer: str (reviewer name)
                - review_reviewer_kind: str ("human" or "agent")
                - review_reviewed_at: str (ISO 8601 timestamp)
                - sources: List[str] (URLs or references)
                - tags: List[str] (additional tags)
                - expires_on: str (ISO 8601 date when entry becomes stale)
        
        Returns:
            Success message with updated fields
        """
        doc_path = self._find_document(doc_id)
        if not doc_path:
            return f"Document {doc_id} not found"

        entry = self._parse_document(doc_path)
        if not entry:
            return f"Document {doc_id} could not be parsed"

        updated_fields = []
        for key, value in metadata.items():
            if key == "volatility":
                if value not in VOLATILITY_LEVELS:
                    return f"Invalid volatility '{value}'. Must be one of: {list(VOLATILITY_LEVELS.keys())}"
                entry.volatility = value
                updated_fields.append(f"volatility={value}")

            elif key == "confidence_basis":
                for basis in value:
                    if basis not in CONFIDENCE_BASIS_TYPES:
                        return f"Invalid confidence_basis '{basis}'. Must be one of: {list(CONFIDENCE_BASIS_TYPES.keys())}"
                entry.confidence_basis = value
                updated_fields.append(f"confidence_basis={value}")

            elif key == "review_status":
                if value not in REVIEW_STATUSES:
                    return f"Invalid review_status '{value}'. Must be one of: {list(REVIEW_STATUSES.keys())}"
                entry.review_status = value
                updated_fields.append(f"review_status={value}")

            elif key == "review_reviewer":
                entry.review_reviewer = value
                updated_fields.append(f"review_reviewer={value}")

            elif key == "review_reviewer_kind":
                if value not in ("human", "agent"):
                    return f"Invalid review_reviewer_kind '{value}'. Must be 'human' or 'agent'"
                entry.review_reviewer_kind = value
                updated_fields.append(f"review_reviewer_kind={value}")

            elif key == "review_reviewed_at":
                entry.review_reviewed_at = value
                updated_fields.append(f"review_reviewed_at={value}")

            elif key == "sources":
                entry.sources = value
                updated_fields.append(f"sources={value}")

            elif key == "tags":
                entry.tags = list(set(entry.tags + value))  # merge, dedupe
                updated_fields.append(f"tags={entry.tags}")

            elif key == "expires_on":
                # expires_on is a CatalogEntry field, store in frontmatter
                updated_fields.append(f"expires_on={value}")

            else:
                return f"Unknown metadata field '{key}'"

        # Write back
        self._write_document(doc_path, entry, metadata)
        return f"Enriched {doc_id}: {', '.join(updated_fields)}"

    def assess_volatility(self, content: str, entry_type: str) -> str:
        """Heuristic volatility assessment based on content and type.
        
        Args:
            content: The document body text
            entry_type: The entry type (explainer, diagram, snippet, prompt, note)
        
        Returns:
            Suggested volatility level
        """
        # Snippets with API endpoints or version numbers are fast
        version_indicators = ["v1", "v2", "v3", "version", "api/", "endpoint", "url", "http"]
        if any(ind in content.lower() for ind in version_indicators):
            return "fast"

        # Explainers about patterns or models are slow
        pattern_indicators = ["pattern", "architecture", "framework", "principle", "mental model"]
        if any(ind in content.lower() for ind in pattern_indicators):
            return "slow"

        # Snippets are generally medium (tool versions change)
        if entry_type == "snippet":
            return "medium"

        # Notes are generally medium
        if entry_type == "note":
            return "medium"

        # Explainers are generally slow
        if entry_type == "explainer":
            return "slow"

        # Default
        return "medium"

    def suggest_confidence_basis(self, content: str, sources: Optional[List[str]] = None) -> List[str]:
        """Suggest confidence basis tags based on content analysis.
        
        Args:
            content: The document body text
            sources: Optional list of source URLs/references
        
        Returns:
            List of suggested confidence basis tags
        """
        basis = []
        content_lower = content.lower()

        if sources and len(sources) > 0:
            basis.append("consensus" if len(sources) >= 2 else "expert")
        
        if any(w in content_lower for w in ["backtest", "empirical", "measured", "validated", "tested"]):
            basis.append("empirical")
        
        if any(w in content_lower for w in ["theory", "theorem", "proof", "mathematical", "framework"]):
            basis.append("theoretical")
        
        if any(w in content_lower for w in ["inferred", "derived", "logical", "therefore", "implies"]):
            basis.append("inferred")
        
        if not basis:
            basis.append("unverified")
        
        return list(set(basis))

    def bulk_enrich(self, dry_run: bool = True) -> Dict[str, List[str]]:
        """Scan all KB entries and suggest metadata enrichments.
        
        Args:
            dry_run: If True, only report suggestions without writing
        
        Returns:
            Dict with 'suggestions' and 'applied' lists
        """
        result = {"suggestions": [], "applied": []}
        
        for md in sorted(self.repo_root.glob("kb/*/*.md")):
            text = md.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            
            parts = text.split("---", 2)
            if len(parts) < 3:
                continue
            
            data = yaml.safe_load(parts[1])
            body = parts[2].strip()
            doc_id = data.get("id", md.stem)
            
            suggestions = []
            
            # Volatility assessment
            current_vol = data.get("volatility", "slow")
            suggested_vol = self.assess_volatility(body, data.get("type", "note"))
            if suggested_vol != current_vol:
                suggestions.append(f"{doc_id}: volatility {current_vol} → {suggested_vol}")
            
            # Confidence basis assessment
            current_basis = data.get("confidence_basis", [])
            if not current_basis:
                suggested_basis = self.suggest_confidence_basis(body, data.get("sources"))
                suggestions.append(f"{doc_id}: confidence_basis → {suggested_basis}")
            
            if suggestions:
                result["suggestions"].extend(suggestions)
                
                if not dry_run:
                    metadata = {}
                    if suggested_vol != current_vol:
                        metadata["volatility"] = suggested_vol
                    if not current_basis:
                        metadata["confidence_basis"] = suggested_basis
                    if metadata:
                        msg = self.enrich_entry(doc_id, metadata)
                        result["applied"].append(msg)
        
        return result

    def _find_document(self, doc_id: str) -> Optional[pathlib.Path]:
        """Find a document by ID in the KB."""
        for md in self.repo_root.glob("kb/*/*.md"):
            if doc_id in md.name:
                return md
        return None

    def _parse_document(self, path: pathlib.Path) -> Optional[KnowledgeEntry]:
        """Parse a markdown file into a KnowledgeEntry."""
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                data = yaml.safe_load(parts[1])
                data["body"] = parts[2].strip()
                data["path"] = str(path.relative_to(self.repo_root))
                try:
                    return KnowledgeEntry(**data)
                except Exception:
                    return None
        return None

    def _write_document(self, path: pathlib.Path, entry: KnowledgeEntry, extra: Dict[str, Any]):
        """Write an enriched entry back to disk."""
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            return
        
        data = yaml.safe_load(parts[1])
        body = parts[2].strip() if len(parts) > 2 else ""
        
        # Update fields from entry
        data["volatility"] = entry.volatility
        data["confidence_basis"] = entry.confidence_basis
        data["review_status"] = entry.review_status
        data["tags"] = entry.tags
        if entry.review_reviewer:
            data["review_reviewer"] = entry.review_reviewer
        if entry.review_reviewer_kind:
            data["review_reviewer_kind"] = entry.review_reviewer_kind
        if entry.review_reviewed_at:
            data["review_reviewed_at"] = entry.review_reviewed_at
        if entry.sources is not None:
            data["sources"] = entry.sources
        
        # Apply extra fields not in KnowledgeEntry model
        if "expires_on" in extra:
            data["expires_on"] = extra["expires_on"]
        
        # Write back
        new_text = "---\n" + yaml.dump(data, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
        path.write_text(new_text, encoding="utf-8")
