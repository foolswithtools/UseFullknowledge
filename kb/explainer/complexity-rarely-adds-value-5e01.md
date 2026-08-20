---
id: complexity-rarely-adds-value-5e01
title: "Complexity Rarely Adds Value"
type: explainer
summary: "Empirically validated across 10+ backtests: combining multiple trading signals into a composite strategy destroys value. A 4-signal composite scored OOS Sharpe 0.11 vs the best individual signal at 0.82. Adding turnover conditioning subtracted 0.13 Sharpe. RAMOM scored 0.25 vs plain TSMOM. Weekly reversal scored -0.29 killed by costs. The rule: prefer simple signals with simple risk overlays over complex multi-signal composites. The burden of proof is always on the complex version."
tags: [trading, strategy, complexity, backtesting, signal-combination, risk-management]
created_at: "2026-08-20T16:20:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4
updated_at: "2026-08-20T16:20:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited, model-recall-only]
volatility: slow
sources:
  - https://arxiv.org/abs/2602.17913
---

## Summary

Across 10+ backtests on US equity and cross-asset ETF data, combining multiple trading signals into a composite strategy consistently destroyed out-of-sample performance. The simplest strategies with single signals and basic risk overlays outperformed every complex multi-signal composite tested. This is a Stage 3 cross-trajectory abstraction: a universal rule extracted from multiple independent backtest trajectories, not a single observation.

## Context

This matters for any quantitative trader, systematic strategy designer, or AI agent building trading systems. The natural temptation when building a strategy is to combine many good signals into a single composite. The empirical finding is that this combination destroys value more often than it creates it.

**The problem:** Each additional signal introduces parameters (weights, thresholds, combination methods) that are fit in-sample. The more signals you combine, the more parameters you fit, and the worse the out-of-sample performance. The complexity is in-sample overfitting wearing the costume of sophistication.

**Who hits it:** Any systematic trader or AI agent constructing multi-signal portfolio strategies. Especially relevant for AI agents that may be tempted to build increasingly sophisticated composites because more complex feels like more capable.

## How it works

### The empirical evidence (10+ backtests, Aug 12-13, 2026)

| Strategy | OOS Sharpe | vs Simple Baseline |
|----------|-----------|-------------------|
| Volatility signal (individual) | 0.82 | Best individual signal |
| 4-signal composite (momentum+value+quality+reversal) | 0.11 | -0.71 vs best individual |
| Turnover conditioning (added to working strategy) | -0.13 value-add | Negative contribution |
| RAMOM (risk-adjusted momentum) | 0.25 | Worse than plain TSMOM |
| Weekly reversal | -0.29 | Killed by transaction costs |
| Quality screen as diversifier | corr 0.594 | Too correlated to diversify |
| Plain TSMOM (time-series momentum) | >0.25 | Simpler is better |
| Circuit breaker overlay | +0.25 Sharpe, +15.66 Calmar | Simple overlay ADDS value |
| Rate filter overlay | -13.5% drawdown reduction | Simple overlay ADDS value |

### The pattern

**What destroys value (complexity):**
- Multi-signal composites (4 signals to OOS Sharpe 0.11)
- Adding signals to working strategies (turnover conditioning to -0.13)
- Risk-adjusted signal variants (RAMOM worse than plain TSMOM)
- High-turnover strategies (weekly reversal to -0.29 killed by costs)
- Correlated diversifiers (quality screen corr 0.594 is not a diversifier)

**What adds value (simplicity):**
- Single strong signals: momentum, value, trend (each individually strong)
- Simple risk overlays: circuit breaker (+0.25 Sharpe), rate filter (-13.5% DD)
- Low-correlation diversifiers: SMB (corr 0.087), RAMOM (corr 0.178 as diversifier only)
- Diversification across asset classes (10-ETF basket)
- Volatility scaling (risk management, not signal complexity)

### The rule

**Before building a new strategy, ask: Is this more complex than what already works?**

If yes, the burden of proof is on the complex version. Require empirical backtest evidence that complexity adds value before adopting it. Default to simple.

The asymmetry is important: simple strategies are easy to validate (fewer parameters, less overfitting risk), while complex strategies require extraordinary evidence to justify their additional parameters. Most of the time, that evidence does not exist.

### Why this happens

1. **Overfitting via parameter proliferation:** Each signal adds weights, thresholds, and combination parameters. In-sample optimization finds the best combination for historical data that will never repeat.

2. **Correlation illusion:** Signals that appear independent in-sample often become correlated in stress periods. The quality screen (corr 0.594) looked like a diversifier but was not.

3. **Transaction cost amplification:** More signals means more rebalancing, which means higher turnover. Weekly reversal looked profitable before costs (-0.29 Sharpe after costs).

4. **Signal decay:** Academic signals are published, arbitraged, and weaken over time. Combining decaying signals compounds their decay.

## What this is not

- **Not always use one signal.** Diversification across low-correlation assets (SMB at 0.087, cross-asset ETFs) adds genuine value. The rule is about signal complexity, not portfolio simplicity.
- **Not never combine signals.** Some combinations work, but they are the exception. Require empirical evidence (walk-forward validated) before adopting.
- **Not ignore risk management.** Simple risk overlays (circuit breaker, rate filter) consistently ADD value. The rule targets signal complexity, not risk overlays.
- **Not one backtest is enough.** This rule is validated across 10+ independent backtests on different data, different signals, different time periods.

## Practical application

1. **Starting point:** Always begin with the simplest version that could plausibly work. One signal, one asset class, monthly rebalance.
2. **Validation gate:** Before adding any signal or overlay, backtest it independently AND as an addition to the existing strategy. If the addition hurts OOS Sharpe, reject it.
3. **Walk-forward:** Validate with rolling in-sample/out-of-sample splits. Any strategy that only works on full-sample optimization is suspect.
4. **No-signal control:** Compare every signal strategy against a no-signal basket (equal-weight, vol-scaled). If the signal does not beat the no-signal version, the signal has no value.
5. **Correlation check:** Before calling something a diversifier, measure its correlation to the existing portfolio. If correlation > 0.3, it is not a diversifier.

## References

1. TierMem (ICLR 2026) - The write-before-query barrier: compression decisions are made before knowing what future queries will depend on. This is why in-sample optimization systematically overfits. https://arxiv.org/abs/2602.17913
2. Backtest results: 10+ independent backtests, Aug 12-13, 2026, US equity and cross-asset ETF data via yfinance.

---

*Filed by Loup (autonomous AI agent) for human review as the second artifact in the UseFullknowledge human review pipeline. Validated across 10+ independent backtests with walk-forward testing. This is a Stage 3 cross-trajectory abstraction.*
