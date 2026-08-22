---
id: autonomous-software-factory-architecture-recommendation-aug-2026-065e
title: "Autonomous Software Factory Architecture Recommendation (Aug 2026)"
type: note
summary: "Recommended architecture for Kevin's Autonomous Software Factory: pipeline pattern with embedded debate at review checkpoints, blackboard state management, LangGraph framework, 3 human-in-the-loop checkpoints. Key principle: build single-agent first, decompose to multi-agent only when evidence demands it."
tags: [autonomous, software-factory, architecture, pipeline, orchestration]
created_at: "2026-08-22T21:20:00+00:00"
created_by_tool: loup
created_by_model: claude-opus-5
updated_at: "2026-08-22T21:20:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [synthetic-example, cross-model-corroborated]
sources: ["https://presenc.ai/research/multi-agent-orchestration-frameworks-2026", "https://explainx.ai/blog/multi-agent-orchestration-patterns-guide-2026", "https://odeaworks.com/blog/2026-04-05-llm-agent-orchestration-patterns/", "https://theaiagentindex.com/compare/factory-ai-vs-devin"]
volatility: ephemeral
---

## Summary

Recommended architecture for Kevin's Autonomous Software Factory based on research into state-of-the-art AI coding agents and multi-agent orchestration patterns. The factory should use a pipeline pattern with embedded debate at security/code review checkpoints, blackboard state management, and 3 human-in-the-loop gates.

## Notes

### Recommended Architecture: Pipeline with Embedded Debate

The factory pipeline: Intake -> Prototype Analyzer -> IaC Generator -> CI/CD Builder -> Security Reviewer -> Deployer.

Why pipeline: phases are a known transformation chain with clear dependencies. Phase 1 must complete before Phase 2. Textbook sequential pipeline.

Fan-out in Phase 1: prototype analysis decomposes into parallel specialized analyzers (language detector, dependency scanner, secret scanner, data model extractor) running in parallel, merging into dossier.json.

Debate in Phase 4: security review is high-stakes correctness. A reviewer agent critiques generated IaC/code, the generator revises. 1-2 rounds. Catches the "AI defaults to 0.0.0.0/0 to make it work" problem.

### State Management: Blackboard Pattern

A shared state object (intake manifest from Phase 0, extended by each phase) acts as a blackboard that every agent reads/writes. Orchestrator controls write access. Durable, auditable, replayable.

### Human-in-the-Loop Checkpoints

1. Post-dossier (end Phase 1): human reviews prototype analysis before IaC generation
2. Post-IaC (end Phase 2): human reviews generated infrastructure before CI/CD
3. Post-security-review (end Phase 4): human approves before deployment

Per Presenc AI: human-checkpoint design is the #3 success factor for multi-agent systems.

### Tool Selection Per Phase

- Phase 1 (Analyzer): Claude Code (1M context, Opus 4.6) for deep codebase analysis
- Phase 2 (IaC): Pulumi AI + ArchGenie for infrastructure generation with OPA/CrossGuard guardrails
- Phase 3 (CI/CD): GitHub Actions templates with tier-specific pipelines
- Phase 4 (Security): GitHub Copilot agentic code review + debate loop
- Phase 5 (Deploy): Manual trigger after human approval

### Framework: LangGraph

38% production market share, best observability via LangSmith, graph-based state machine maps to pipeline pattern, checkpointing built-in.

### Build Single-Agent First Principle

"The most expensive multi-agent system is one that does not need to be multi-agent." Build a single Claude Code session that does intake -> analysis -> IaC -> CI/CD -> security review sequentially. Learn what it requires. Decompose into multi-agent only when there is evidence single-agent is insufficient. This connects with the complexity rule from trading: prefer simple over complex unless complexity is proven to add value.

### What Makes Kevin's Factory Unique

No existing tool does: full pipeline, tier-based policy bundles, standards precedence, CMDB-informed generation, prototype dossier, or 3-checkpoint human gates. Factory's value = orchestration + tier policies + standards enforcement, not code generation.

### Source Provenance
- presenc.ai: Framework comparison, success factors
- explainx.ai: Five core patterns, "build single-agent first" principle
- odeaworks.com: Four pattern categories with real-world implementations
- theaiagentindex.com: Factory AI vs Devin landscape

## Open questions

1. Should the factory use LangGraph or custom Python orchestration?
2. What evaluation infrastructure is needed for each pipeline phase?
3. How do human checkpoints integrate with the orchestrator programmatically?
4. What is the minimum viable single-agent version before decomposing?
