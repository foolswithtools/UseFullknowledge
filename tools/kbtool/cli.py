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
