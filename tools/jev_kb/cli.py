#!/usr/bin/env python3
"""TypeSafe Jev batch import/export CLI.

Usage:
  jev-kb export [--out FILE]          Export all KB documents as JSONL
  jev-kb import FILE [--dry-run]      Import documents from JSONL file
  jev-kb check                         Run KB validation check
  jev-kb search [--tag T] [--type T]  Search KB documents

All import operations validate via Pydantic before writing.
"""
import sys
import argparse
import pathlib

def main():
    parser = argparse.ArgumentParser(
        prog="jev-kb",
        description="TypeSafe Jev batch import/export utilities for UseFullknowledge KB"
    )
    parser.add_argument("--root", default=".", help="Path to UseFullknowledge repo root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export
    exp = subparsers.add_parser("export", help="Export all KB documents as JSONL")
    exp.add_argument("--out", "-o", help="Output file (default: stdout)")

    # import
    imp = subparsers.add_parser("import", help="Import documents from JSONL file")
    imp.add_argument("file", help="JSONL file to import")
    imp.add_argument("--dry-run", action="store_true", help="Validate only, don't write files")

    # check
    subparsers.add_parser("check", help="Run KB validation check")

    # search
    srch = subparsers.add_parser("search", help="Search KB documents")
    srch.add_argument("--tag", help="Filter by tag")
    srch.add_argument("--type", help="Filter by type (explainer, diagram, snippet, prompt, note)")
    srch.add_argument("--status", help="Filter by review status (unreviewed, verified, rejected)")

    args = parser.parse_args()

    # Import the client library
    sys.path.insert(0, str(pathlib.Path(args.root) / "tools"))
    from jev_kb import JevKBClient

    client = JevKBClient(repo_root=args.root)

    if args.command == "export":
        jsonl = client.export_jsonl()
        if args.out:
            pathlib.Path(args.out).write_text(jsonl + "\n", encoding="utf-8")
            count = jsonl.count("\n") + 1 if jsonl else 0
            print(f"Exported {count} documents to {args.out}", file=sys.stderr)
        else:
            print(jsonl)

    elif args.command == "import":
        content = pathlib.Path(args.file).read_text(encoding="utf-8")
        if args.dry_run:
            # Validate only
            import json
            from jev_kb.models import KnowledgeEntry
            valid = 0
            errors = []
            for line_num, line in enumerate(content.strip().splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    KnowledgeEntry(**data)
                    valid += 1
                except Exception as e:
                    errors.append(f"Line {line_num}: {e}")
            print(f"Dry run: {valid} valid, {len(errors)} errors", file=sys.stderr)
            for err in errors:
                print(f"  {err}", file=sys.stderr)
            if errors:
                sys.exit(1)
        else:
            result = client.import_jsonl(content)
            print(f"Imported: {result.imported}, Failed: {result.failed}", file=sys.stderr)
            if result.errors:
                for err in result.errors:
                    print(f"  {err}", file=sys.stderr)
            if result.failed > 0:
                sys.exit(1)
            print(f"Imported IDs: {', '.join(result.imported_ids)}", file=sys.stderr)

    elif args.command == "check":
        report = client.check()
        print(report["raw"])
        if not report["valid"]:
            sys.exit(1)

    elif args.command == "search":
        results = client.search(tag=args.tag, type=args.type, status=args.status)
        if not results:
            print("No documents found", file=sys.stderr)
        for r in results:
            print(f"  {r.id}  [{r.type}]  ({r.review_status})  {r.title}")

if __name__ == "__main__":
    main()
