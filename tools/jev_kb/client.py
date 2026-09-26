"""JevKBClient — type-safe wrapper around kbtool CLI subprocess calls."""
from __future__ import annotations
import json, subprocess, pathlib, yaml
from typing import List, Optional
from .models import KnowledgeEntry, SearchResult, CatalogEntry, BatchImportResult

class JevKBClient:
    def __init__(self, repo_root: str = "."):
        self.repo_root = pathlib.Path(repo_root)
        self._kb_script = self.repo_root / "tools" / "kb.py"

    def _run_kb(self, *args: str) -> subprocess.CompletedProcess:
        cmd = ["python3", str(self._kb_script), "--root", str(self.repo_root)] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    def check(self) -> dict:
        proc = self._run_kb("check")
        output = proc.stdout + proc.stderr
        errors = [l for l in output.splitlines() if "error" in l.lower() and "0 error" not in l]
        warnings = [l for l in output.splitlines() if "warning" in l.lower() and "0 warning" not in l]
        return {"valid": proc.returncode == 0, "errors": errors, "warnings": warnings, "raw": output}

    def search(self, tag: Optional[str] = None, type: Optional[str] = None, status: Optional[str] = None) -> List[SearchResult]:
        args = ["search"]
        if tag: args.extend(["--tag", tag])
        if type: args.extend(["--type", type])
        if status: args.extend(["--status", status])
        proc = self._run_kb(*args)
        results = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or "document(s) found" in line or line.startswith("No documents"): continue
            parts = line.split()
            if len(parts) < 5: continue
            results.append(SearchResult(id=parts[0], title=" ".join(parts[3:]), type=parts[1].strip("[]"), tags=[], review_status=parts[2].strip("()"), path=f"kb/{parts[1].strip('[]')}/{parts[0]}.md"))
        return results

    def get(self, doc_id: str) -> Optional[KnowledgeEntry]:
        for md in self.repo_root.glob("kb/*/*.md"):
            if doc_id in md.name:
                return self._parse_document(md.read_text(encoding="utf-8"), str(md.relative_to(self.repo_root)))
        return None

    def _parse_document(self, text: str, path: str) -> KnowledgeEntry:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                data = yaml.safe_load(parts[1]); data["body"] = parts[2].strip(); data["path"] = path
                return KnowledgeEntry(**data)
        return KnowledgeEntry(**yaml.safe_load(text))

    def create(self, doc_type: str, title: str, tool: str, model: str) -> str:
        proc = self._run_kb("new", doc_type, title, "--tool", tool, "--model", model)
        if proc.returncode != 0: raise RuntimeError(f"kb new failed: {proc.stderr}")
        return proc.stdout.strip()

    def update(self, doc_id: str, fields: dict, reviewer: Optional[str] = None, reviewer_kind: Optional[str] = None) -> str:
        args = ["update", doc_id]
        for k, v in fields.items(): args.extend(["--set", f"{k}={v}"])
        if reviewer: args.extend(["--reviewer", reviewer])
        if reviewer_kind: args.extend(["--reviewer-kind", reviewer_kind])
        proc = self._run_kb(*args)
        if proc.returncode != 0: raise RuntimeError(f"kb update failed: {proc.stderr}")
        return proc.stdout.strip()

    def list_all(self) -> List[SearchResult]: return self.search()
    def list_by_type(self, doc_type: str) -> List[SearchResult]: return self.search(type=doc_type)
    def list_verified(self) -> List[SearchResult]: return self.search(status="verified")

    def export_jsonl(self) -> str:
        lines = []
        for md in sorted(self.repo_root.glob("kb/*/*.md")):
            text = md.read_text(encoding="utf-8")
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    data = yaml.safe_load(parts[1]); data["body"] = parts[2].strip()
                    data["path"] = str(md.relative_to(self.repo_root))
                    lines.append(json.dumps(data, ensure_ascii=False))
        return "\n".join(lines)

    def import_jsonl(self, jsonl_content: str) -> BatchImportResult:
        result = BatchImportResult()
        for line_num, line in enumerate(jsonl_content.strip().splitlines(), 1):
            if not line.strip(): continue
            try:
                data = json.loads(line); entry = KnowledgeEntry(**data)
                doc_path = self.repo_root / "kb" / entry.type / f"{entry.id}.md"
                doc_path.parent.mkdir(parents=True, exist_ok=True)
                fm = {k: v for k, v in data.items() if k not in ("body", "path")}
                md_content = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + data.get("body", "") + "\n"
                doc_path.write_text(md_content, encoding="utf-8")
                result.imported += 1; result.imported_ids.append(entry.id)
            except Exception as e:
                result.failed += 1; result.errors.append(f"Line {line_num}: {str(e)}")
        return result
