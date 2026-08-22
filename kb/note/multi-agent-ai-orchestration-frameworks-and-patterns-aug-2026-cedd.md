---
id: multi-agent-ai-orchestration-frameworks-and-patterns-aug-2026-cedd
title: "Multi-Agent AI Orchestration Frameworks and Patterns (Aug 2026)"
type: note
summary: "Comparison of multi-agent AI orchestration frameworks (LangGraph, CrewAI, AutoGen, OpenAI Swarm) and five core orchestration patterns (orchestrator/worker, pipeline, fan-out/fan-in, debate, specialist routing). Includes state management, error handling, and when NOT to use multi-agent. Directly applicable to Autonomous Software Factory pipeline design."
tags: [multi-agent, orchestration, langgraph, crewai, software-factory, architecture]
created_at: "2026-08-22T21:09:00+00:00"
created_by_tool: loup
created_by_model: claude-opus-5
updated_at: "2026-08-22T21:09:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [secondary-source-cited, executed-verified]
sources: ["https://presenc.ai/research/multi-agent-orchestration-frameworks-2026", "https://explainx.ai/blog/multi-agent-orchestration-patterns-guide-2026", "https://odeaworks.com/blog/2026-04-05-llm-agent-orchestration-patterns/"]
volatility: ephemeral
---

## Summary

How do multi-agent AI orchestration frameworks work, what patterns exist for coordinating specialized agents in a pipeline, and which framework/pattern is right for the Autonomous Software Factory?

## Notes

### Framework Landscape (Q1 2026)

| Framework | Prod Share | Strengths | Weaknesses |
|-----------|-----------|-----------|------------|
| LangGraph | ~38% | Graph-based state machine, supervisor pattern, LangSmith observability | Learning curve, LangChain coupling |
| Custom (Python/TS) | ~28% | No lock-in, full control | Reinvents wheels |
| CrewAI | ~12% | Intuitive role-based crew abstraction | Weak observability, no checkpointing |
| AutoGen | ~9% | Conversational agents, debate patterns | Less standardized |
| Claude Skills | ~5% | Anthropic-native | Ecosystem-limited |
| Google ADK | ~4% | GCP-native | Smaller community |
| OpenAI Swarm | ~2% | Minimal, easy | Experimental, not production |

Key insight: Framework choice is less consequential than model selection, evaluation infrastructure, and human-checkpoint design (which rank 1-3).

### Five Core Orchestration Patterns

1. **Orchestrator/Worker**: 1 planner delegates to N specialized workers, aggregates results. Good starting point for most production systems.
2. **Pipeline/Sequential**: A to B to C to D. Each agent hands off output as input. Like Unix pipes. Intermediate outputs must be structured (JSON schema).
3. **Parallel Fan-Out/Fan-In**: Same task to N agents in parallel, aggregate by voting/merging/best. N agents = N times token cost.
4. **Peer-to-Peer/Debate**: Agent A produces, Agent B critiques, A revises. One round usually sufficient. Good for high-stakes correctness (security review).
5. **Specialist Routing**: Router classifies task, dispatches to right specialist. Router should be small/fast model.

### Critical Implementation Details

**State Management**: Three levels: per-agent (conversation history, keep minimal), shared (work product passed between agents), global (task status, orchestrator-owned). Blackboard pattern: shared dict every agent reads/writes, orchestrator controls write access.

**Error Handling**: In a 5-agent system with 5% failure rate each, ~23% chance of at least one failure per run. Design for failure: retry with backoff, graceful degradation, circuit breakers.

**Cost Management**: Model selection per agent (cheapest acceptable quality), context pruning, budget limits, parallel efficiency.

**When NOT to use multi-agent**: Task fits in one context window, latency matters more than quality, workflow is simple and linear, still figuring out the task (build single-agent first).

### Application to Autonomous Software Factory

Recommended architecture: Pipeline (sequential) with embedded Debate at critical checkpoints.

Factory pipeline: Intake to Prototype Analyzer to IaC Generator to CI/CD Builder to Security Reviewer to Deployer.

- Fan-out in Phase 1: multiple specialized analyzers (language, deps, secrets, data model) in parallel
- Debate in Phase 4: reviewer critiques generated IaC, generator revises, 1-2 rounds
- Blackboard state management: shared state object, orchestrator controls writes
- Human-in-the-loop at 3 checkpoints: post-dossier, post-IaC, post-security-review
- Framework: LangGraph (38% market share, best observability, graph-based state machine)

Critical warning: "The most expensive multi-agent system is one that does not need to be multi-agent." Build single-agent version first (one Claude Code session doing all phases sequentially), decompose only when there is evidence single-agent is insufficient.

### Source Provenance
- presenc.ai/research/multi-agent-orchestration-frameworks-2026: Framework comparison
- explainx.ai/blog/multi-agent-orchestration-patterns-guide-2026: Five core patterns with code
- odeaworks.com/blog/2026-04-05-llm-agent-orchestration-patterns/: Four pattern categories with implementations

## Open questions

1. How does LangGraph checkpointing perform at scale (100+ steps)?
2. What is the token cost overhead of multi-agent vs single-agent for typical factory workloads?
3. How do debate patterns perform when the critic and generator use the same model vs different models?
4. What evaluation infrastructure is needed for the factory pipeline specifically?
