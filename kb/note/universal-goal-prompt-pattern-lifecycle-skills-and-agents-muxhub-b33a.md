---
id: universal-goal-prompt-pattern-lifecycle-skills-and-agents-muxhub-b33a
title: "Universal Goal Prompt Pattern — Lifecycle, Skills, and Agents (muxhub)"
type: note
summary: "The Universal Goal Prompt Pattern extracted from muxhub's development (640 commits, 218 PRs, 76 issues, 63 spec docs over 5 months). Core principle: every unit of work has a written, self-contained spec that a fresh agent with zero context can execute. Includes full lifecycle (research goal prompt → decision-ready spec → issue authoring → TDD execution → whole-branch review → merge gate → close-out), three-layer context architecture (GitHub issues, repo docs, agent memory), and four skill definitions."
tags: [universal-goal-prompt, muxhub, pattern, lifecycle, tdd, whole-branch-review, issue-driven-development, context-layering, goal-prompts]
created_at: "2026-08-22T22:10:00+00:00"
created_by_tool: loup
created_by_model: claude-opus-5
updated_at: "2026-08-22T22:10:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [secondary-source-cited]
sources: ["https://github.com/foolswithtools/muxhub-private"]
volatility: evergreen
---

## Summary

The Universal Goal Prompt Pattern is the working methodology extracted from building muxhub (~640 commits, 218 merged PRs with zero abandoned, 76 issues, 63 spec docs, 70 plan docs over 5 months). Every unit of work gets a written, self-contained spec that a fresh agent with zero context can execute. The spec carries its own context via embedded file:line anchors, verbatim interfaces, and dated observations, or by reference into the repo. Transcripts are disposable; the repo is the memory.

## Notes

### Core Principle

Every unit of work has a written spec that a fresh agent with no prior context can execute, and the spec carries its own context — either embedded (file:line anchors, verbatim interfaces, dated observations) or by reference into the repo.

### The Lifecycle

1. Research goal prompt → decision-ready spec in docs/specs/
2. Decision resolution with human (batched questions, recommended defaults, answers recorded INTO spec)
3. Issue-authoring goal prompt → self-contained GitHub issues + tracker DAG (before any code)
4. Fresh-session kickoff ("complete issue #N in TDD manner, do not merge until CI green")
5. Execution: brainstorm → plan → parallel TDD subagent slices (wire contract, allowed-files, pasted RED output)
6. Per-task review → whole-branch review by fresh-context agent
7. PR (Closes #N, evidence-carrying body) → CI green → HUMAN merge gate
8. Close-out: follow-up issues, docs hygiene, lesson extraction, memory append, handoff prompt if work continues

### Cross-Cutting Invariants

1. Staleness protocol: every context artifact is dated, re-verify file:line claims
2. Negative space is first-class: "What already exists (do not rebuild)", "Do NOT do", "Standing decisions"
3. Evidence before assertions: never claim a gate passed without real command output
4. Verify at the real surface, not only against fakes
5. Failure history is transferred: handoff prompts spell out why previous attempt died
6. Amend in place with dated addenda, never silent deletion
7. Failure honesty: process lapses get their own issues
8. Casual work stays casual: heavyweight machinery reserved for units of work

### Three-Layer Context Architecture

| Layer | Holds | Never holds |
|---|---|---|
| GitHub issues/PRs | Units of work, decisions, dependency DAGs | Long-form shared design context |
| Repo docs | Durable truth: specs, plans, roadmap, lessons | Session-specific state |
| Agent memory | Cross-session state, infra facts, process lessons | Anything a fresh session elsewhere needs |

### Skills Included

1. issue-driven-development: the full lifecycle as executable process
2. writing-goal-prompts: authoring briefs a cold agent can execute
3. whole-branch-review: fresh-context merge safety net (catches every merge-blocker per-task reviews miss)
4. context-layering: where context lives and lesson extraction

### Agents Included

1. issue-author: turns accepted spec into self-contained GitHub issues
2. slice-implementer: executes one TDD slice under wire contract
3. branch-reviewer: whole-branch, cross-task-wiring review before merge

### Key Evidence

- 75% of 76 issues cite code paths, 36% cite exact line numbers, 53% reference docs/ files
- 89% of feature/fix commits touch tests in same commit
- 215/218 PR bodies carry attribution footer
- Zero abandoned PRs out of 218 merged
- Whole-branch review caught every merge-blocker that per-task reviews and green suites missed

### Source Provenance
- COMBINED.md shared by TODS via Slack #aios-loup (Aug 22, 2026)
- Origin: github.com/foolswithtools/muxhub-private
- Extracted by four-agent analysis of Claude Code session transcripts, git history, GitHub issue/PR history, and goal-prompt/memory/docs corpus

## Open questions

1. How does this pattern adapt for non-Claude-Code agents (agy, Cursor, Copilot)?
2. What parts of the lifecycle are essential vs optional for small projects?
3. How does the three-layer context architecture map to UseFullknowledge as the repo docs layer?
