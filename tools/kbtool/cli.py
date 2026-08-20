"""Command line entry point: ``kb check``, ``kb build``, ``kb new``.

Validation gates the build. A document with missing or dishonest provenance can
never reach the published site, because ``build`` refuses to write anything
until ``check`` is clean.
"""

import argparse
import datetime
import pathlib
import re
import sys

from kbtool.identity import make_id, slugify
from kbtool.render import build_site
from kbtool.validate import ERROR, validate_repo

CONTENT_TYPES = ("explainer", "diagram", "snippet", "prompt", "note")


def _today(args):
    return args.today or datetime.date.today().isoformat()


def _print_report(report, stream):
    for finding in report.findings:
        print(finding.format(), file=stream)
    errors, warnings = len(report.errors), len(report.warnings)
    if errors or warnings:
        print(f"\n{errors} error(s), {warnings} warning(s)", file=stream)
    else:
        print("All documents valid.", file=stream)


def cmd_check(args):
    report = validate_repo(args.root, today=_today(args))
    _print_report(report, sys.stdout)
    return 1 if report.has_errors else 0


def cmd_build(args):
    report = validate_repo(args.root, today=_today(args))
    if report.has_errors:
        _print_report(report, sys.stderr)
        print("\nRefusing to build: fix the errors above.", file=sys.stderr)
        return 1
    for finding in report.warnings:
        print(finding.format())
    out = args.out or str(pathlib.Path(args.root) / "_site")
    entries = build_site(args.root, out, today=_today(args))
    print(f"Built {len(entries)} document(s) into {out}")
    return 0


def cmd_new(args):
    root = pathlib.Path(args.root)
    template = root / "templates" / f"{args.type}.md"
    if not template.exists():
        print(f"No template for type '{args.type}' at {template}", file=sys.stderr)
        return 1

    now = args.now or datetime.datetime.now().astimezone().replace(
        microsecond=0).isoformat()
    doc_id = make_id(args.title, args.tool, now)
    text = template.read_text(encoding="utf-8")

    replacements = {
        "id": doc_id,
        "title": f'"{args.title}"',
        "summary": '"TODO: one paragraph describing what this document explains."',
        "tags": f"[{slugify(args.title).split('-')[0]}]",
        "created_at": f'"{now}"',
        "created_by_tool": args.tool,
        "created_by_model": args.model,
        "updated_at": f'"{now}"',
    }
    for key, value in replacements.items():
        text = re.sub(rf"^{key}:.*$", f"{key}: {value}", text, count=1, flags=re.MULTILINE)

    target = root / "kb" / args.type / f"{doc_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"Created {target.relative_to(root)}")
    print("Now fill in every TODO, then run: python3 tools/kb.py check")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kb", description="UseFullknowledge tooling")
    parser.add_argument("--root", default=".", help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate every document")
    check.add_argument("--today", help="ISO date used for staleness (testing)")
    check.set_defaults(func=cmd_check)

    build = sub.add_parser("build", help="validate, then render the site")
    build.add_argument("--today", help="ISO date used for staleness (testing)")
    build.add_argument("--out", help="output directory (default _site)")
    build.set_defaults(func=cmd_build)

    new = sub.add_parser("new", help="scaffold a document from a template")

    # update — change frontmatter fields on an existing document
    update = sub.add_parser("update", help="update frontmatter on an existing document")
    update.add_argument("id", help="Document id (or partial id to match)")
    update.add_argument("--set", action="append", default=[],
                        help="Set a frontmatter field: --set key=value")
    update.add_argument("--reviewer", default=None, help="Set review_reviewer")
    update.add_argument("--reviewer-kind", default=None, help="Set review_reviewer_kind")
    update.add_argument("--now", default=None, help="Override updated_at timestamp")

    # search — query documents locally without HTTPS
    search = sub.add_parser("search", help="search documents locally")
    search.add_argument("--tag", default=None, help="Filter by tag")
    search.add_argument("--type", default=None, help="Filter by document type")
    search.add_argument("--status", default=None, help="Filter by review_status")
    search.set_defaults(func=cmd_search)
    update.set_defaults(func=cmd_update)
    new.add_argument("type", choices=CONTENT_TYPES)
    new.add_argument("title")
    new.add_argument("--tool", required=True, help="the tool filing this, e.g. claude-code")
    new.add_argument("--model", required=True, help="the model, e.g. claude-opus-5")
    new.add_argument("--now", help="ISO timestamp with offset (defaults to now)")
    new.set_defaults(func=cmd_new)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())


def cmd_update(args):
    """Update frontmatter fields on an existing document.

    Usage: kb update <id> --set key=value [--reviewer name --reviewer-kind kind] [--now TS]
    """
    import datetime
    from .frontmatter import parse, dump
    from .identity import resolve_id

    root = pathlib.Path(args.root) if args.root else pathlib.Path.cwd()
    doc_path = resolve_id(root, args.id)
    if doc_path is None:
        print(f"Error: no document matching id '{args.id}'")
        return 1

    text = doc_path.read_text()
    doc = parse(text)

    # Parse --set key=value pairs
    allowed_fields = {
        "review_status", "review_reviewer", "review_reviewer_kind",
        "review_reviewed_at", "confidence_basis", "volatility",
        "tags", "summary", "title",
    }
    for pair in (args.set or []):
        if "=" not in pair:
            print(f"Error: --set expects key=value, got '{pair}'")
            return 1
        key, val = pair.split("=", 1)
        if key not in allowed_fields:
            print(f"Error: unknown field '{key}'. Allowed: {sorted(allowed_fields)}")
            return 1
        # Parse YAML value
        import yaml as _yaml
        try:
            parsed_val = _yaml.safe_load(val)
        except Exception:
            parsed_val = val
        doc.data[key] = parsed_val

    # Handle --reviewer and --reviewer-kind as shortcuts
    if args.reviewer:
        doc.data["review_reviewer"] = args.reviewer
    if args.reviewer_kind:
        doc.data["review_reviewer_kind"] = args.reviewer_kind

    # Refresh updated_at
    if args.now:
        doc.data["updated_at"] = args.now
    else:
        doc.data["updated_at"] = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()

    # Write back
    doc_path.write_text(dump(doc))
    print(f"Updated: {doc_path.relative_to(root)}")
    return 0


def cmd_search(args):
    """Search documents locally by tag, type, review_status, or list all.

    Usage: kb search [--tag TAG] [--type TYPE] [--status STATUS]
    """
    from .frontmatter import parse

    root = pathlib.Path(args.root) if args.root else pathlib.Path.cwd()
    results = []
    for md in sorted(root.glob("kb/*/*.md")):
        text = md.read_text()
        doc = parse(text)
        data = doc.data

        if args.tag and args.tag not in data.get("tags", []):
            continue
        if args.type and data.get("type") != args.type:
            continue
        if args.status and data.get("review_status") != args.status:
            continue

        results.append({
            "id": data.get("id", "?"),
            "title": data.get("title", "?"),
            "type": data.get("type", "?"),
            "tags": data.get("tags", []),
            "review_status": data.get("review_status", "?"),
            "path": str(md.relative_to(root)),
        })

    if not results:
        print("No documents found.")
        return 0

    for r in results:
        print(f"  {r['id']:50s}  [{r['type']:10s}]  ({r['review_status']:10s})  {r['title']}")
    print(f"\n{len(results)} document(s) found.")
    return 0
