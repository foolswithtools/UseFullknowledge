---
id: why-format-date-time-silently-accepts-anything-in-jsonschema-700c
title: "Why format: date-time silently accepts anything in jsonschema"
type: note
summary: "Raw investigation notes: jsonschema does not enforce any format keyword unless the matching optional validator package is installed, so a schema that appears to require a timezone offset requires nothing at all."
tags: [jsonschema, validation, python]
created_at: "2026-08-14T14:36:00+00:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-09-09T17:39:20+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [executed-verified]
volatility: slow
---

## Summary

Chasing why a schema that looked like it required ISO 8601 timestamps with a
timezone offset was accepting bare dates. The answer is that `format` in JSON
Schema is an *annotation* by default, and `jsonschema` only turns it into an
assertion when the relevant optional dependency is present.

## Notes

Tested directly on this machine, Python 3.12.3 with `jsonschema` 4.10.3:

| Schema | Value | Result |
|---|---|---|
| `{"format": "date-time"}` | `"2026-08-14"` | **accepted** |
| `{"format": "uri"}` | `"not a url at all"` | **accepted** |
| `{"format": "email"}` | `"nope"` | **accepted** |

`import rfc3339_validator` fails — the package is absent, which is what makes
`date-time` inert. The same mechanism applies to `uri` (needs `rfc3987`) and
`email` (needs `fqdn`/`idna` depending on version).

This is documented behaviour, not a bug: the spec says `format` is an annotation
unless a validator opts into assertion, and `jsonschema` opts in per-format only
when it can actually check the format. The trap is that it fails **open** and
**silently** — no warning, no error, just a schema that quietly validates
nothing. A schema author reading their own file sees a constraint that is not
there.

Two other YAML/JSON traps found in the same session, worth writing up properly:

- PyYAML resolves unquoted ISO timestamps to `datetime` objects and re-emits
  them with a space instead of `T`, so a regex check on the "raw" value can be
  inspecting text the author never wrote.
- Python's `str.splitlines()` splits on `\x1e` (ASCII record separator) as well
  as `\n`, which silently destroys `\x1e`-delimited `git log --pretty` output.
  `split("\n")` is the fix.

## Open questions

- Is there a way to make `jsonschema` fail loudly when an unenforceable `format`
  is used, rather than silently ignoring it? A schema-lint pass that greps for
  `"format":` and checks the corresponding package is importable would work, but
  it feels like something the library should offer.
- `FormatChecker` can be passed explicitly — does that raise on unknown formats,
  or also degrade quietly? Not yet tested.

<!--
Raw note. The conclusion here is solid because it was executed, but the "open
questions" are genuinely open and nobody has reviewed any of this.
-->
