---
id: TODO-run-kb-new-or-use-slug-plus-4-hex
title: "TODO: what this diagram shows"
type: diagram
summary: "TODO: one paragraph describing the system and the level of detail shown."
tags: [TODO-topic]
diagram_notation: mermaid
diagram_kind: c4
c4_level: container
subject_system: TODO-system-slug
created_at: "TODO-run: date -Iseconds"
created_by_tool: TODO-your-tool-name
created_by_model: TODO-your-model-id
updated_at: "TODO-same-as-created_at-on-a-new-document"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only]
volatility: slow
---

## Summary

TODO: what this diagram shows and when to look at it.

## Diagram

```mermaid
C4Container
    title Container diagram for TODO

    Person(user, "User", "Someone who uses the system")

    Container_Boundary(sys, "TODO System") {
        Container(web, "Web App", "TODO tech", "TODO responsibility")
        ContainerDb(db, "Database", "TODO tech", "TODO what it stores")
    }

    Rel(user, web, "Uses", "HTTPS")
    Rel(web, db, "Reads/writes", "TODO protocol")
```

## Notes

TODO: anything the diagram cannot say for itself - constraints, things
deliberately omitted, decisions still open.

<!--
`diagram_kind` values: c4, sequence, er, flowchart, state, class, architecture.
`c4_level` and `subject_system` are required only when diagram_kind is c4.
For a C4 set, use the same `subject_system` slug across every level so the
levels can be found together:  rg -l 'subject_system: your-system' kb/
-->
