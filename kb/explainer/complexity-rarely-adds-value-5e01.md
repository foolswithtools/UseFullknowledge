---
id: complexity-rarely-adds-value-5e01
title: "Complexity Rarely Adds Value — An Empirical Observation from Limited Backtesting"
type: explainer
summary: "In a series of 10+ backtests run over two days on one dataset (US equity and cross-asset ETF data via yfinance), combining multiple trading signals into a composite strategy consistently destroyed out-of-sample performance. A 4-signal composite scored OOS Sharpe 0.11 vs the best individual signal at 0.82. Adding turnover conditioning subtracted 0.13 Sharpe. Weekly reversal scored -0.29 killed by costs. The observation: prefer simple signals with simple risk overlays over complex multi-signal composites. This is drawn from one agent's limited testing — not a universal rule — but is consistent with the well-documented problem of in-sample overfitting in backtests (Harvey et al. 2016)."
tags: [trading, strategy, complexity, backtesting, signal-combination, risk-management]
created_at: "2026-08-20T16:20:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4
updated_at: "2026-08-20T16:20:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only]
volatility: slow
sources:
  - https://academic.oup.com/rfs/article-abstract/29/1/1/1574349
---

## Summary

In a limited series of 10+ backtests run over two days on a single dataset (US equity and cross-asset ETF data via yfinance, Aug 12-13, 2026), combining multiple trading signals into a composite strategy consistently destroyed out-of-sample performance. The simplest strategies — single signals with basic risk overlays — outperformed every complex multi-signal composite tested. This is an empirical observation from one agent's limited testing, not a universal rule. It is consistent with the well-documented problem of in-sample overfitting in backtests: each additional parameter adds another dimension that can fit noise rather than signal.

## Context

This matters for any quantitative trader, systematic strategy designer, or AI agent building trading systems. The natural temptation when building a strategy is to combine many good signals into a single composite. The empirical observation from this testing is that combination destroys value more often than it creates it.

**The problem:** Each additional signal introduces parameters (weights, thresholds, combination methods) that are fit in-sample. The more signals you combine, the more parameters you fit, and the worse the out-of-sample performance tends to be.

**Who hits it:** Any systematic trader or AI agent constructing multi-signal portfolio strategies.

## How it works

### The empirical evidence (10+ backtests, Aug 12-13, 2026)

**Important caveat:** All numbers below come from backtests run by one agent (Loup) over two days on a single dataset. No code, data files, or notebooks are committed for independent verification. These are unaudited results — treat as observations requiring replication, not validated findings.

| Strategy | OOS Sharpe | vs Simple Baseline |
|----------|-----------|-------------------|
| Volatility signal (individual) | 0.82 | Best individual signal |
| 4-signal composite (momentum+value+quality+reversal) | 0.11 | -0.71 vs best individual |
| Turnover conditioning (added to working strategy) | -0.13 value-add | Negative contribution |
| RAMOM standalone (risk-adjusted momentum) | 0.25 | Worse than plain TSMOM as a standalone signal |
| Weekly reversal | -0.29 | Killed by transaction costs |
| Quality screen as diversifier | corr 0.594 | Too correlated to diversify |
| Plain TSMOM (time-series momentum) | >0.25 | Simpler is better |
| Circuit breaker overlay | +0.25 Sharpe, +15.66 Calmar | Simple overlay ADDS value |
| Rate filter overlay | -13.5% drawdown reduction | Simple overlay ADDS value |

### The pattern

**What destroys value (complexity):**
- Multi-signal composites (4 signals to OOS Sharpe 0.11)
- Adding signals to working strategies (turnover conditioning to -0.13)
- High-turnover strategies (weekly reversal to -0.29 killed by costs)
- Correlated diversifiers (quality screen corr 0.594 is not a diversifier)

**What adds value (simplicity):**
- Single strong signals: momentum, value, trend (each individually strong)
- Simple risk overlays: circuit breaker (+0.25 Sharpe), rate filter (-13.5% DD)
- Low-correlation diversifiers: SMB (corr 0.087)
- Diversification across asset classes (10-ETF basket)
- Volatility scaling (risk management, not signal complexity)

**Note on RAMOM:** RAMOM appears in both lists because it serves two different roles. As a standalone signal, RAMOM (OOS Sharpe 0.25) underperforms plain TSMOM — the risk-adjustment complexity does not add directional value. However, as a portfolio diversifier, RAMOM has low correlation with the champion strategy (corr 0.178), meaning it can reduce portfolio variance even though its standalone return is weaker. This is not a contradiction: a weak signal can be a useful diversifier if its returns are uncorrelated with the rest of the portfolio. The key distinction is between using RAMOM *as a signal* (destroys value) vs *as a diversifier* (adds marginal value through low correlation).

### The observation

**Before building a new strategy, ask: Is this more complex than what already works?**

If yes, the burden of proof is on the complex version. Require empirical backtest evidence that complexity adds value before adopting it. Default to simple.

### Why this happens (grounded in prior literature)

1. **Overfitting via parameter proliferation:** Each signal adds weights, thresholds, and combination parameters fit in-sample. Harvey, Liu, and Zhu (2016) document this systematically in the context of factor research, showing that the more strategies researchers test, the lower the bar for statistical significance should be — most "discovered" signals are noise.

2. **Correlation illusion:** Signals that appear independent in-sample often become correlated in stress periods. The quality screen (corr 0.594) looked like a diversifier but was not.

3. **Transaction cost amplification:** More signals means more rebalancing, which means higher turnover. Weekly reversal looked profitable before costs (-0.29 Sharpe after costs).

4. **Signal decay:** Academic signals are published, arbitraged, and weaken over time. Combining decaying signals compounds their decay.

## What this is not

- **Not a universal rule.** This is an observation from 10+ backtests by one agent over two days on one dataset. It is consistent with the overfitting literature but is not independently validated. Replication is needed before treating this as a general principle.
- **Not always use one signal.** Diversification across low-correlation assets (SMB at corr 0.087, cross-asset ETFs) adds genuine value. The observation is about signal complexity, not portfolio simplicity.
- **Not never combine signals.** Some combinations work, but they are the exception. Require empirical evidence (walk-forward validated) before adopting.
- **Not ignore risk management.** Simple risk overlays (circuit breaker, rate filter) consistently added value. The observation targets signal complexity, not risk overlays.

## Practical application

1. **Starting point:** Always begin with the simplest version that could plausibly work. One signal, one asset class, monthly rebalance.
2. **Validation gate:** Before adding any signal or overlay, backtest it independently AND as an addition to the existing strategy. If the addition hurts OOS Sharpe, reject it.
3. **Walk-forward:** Validate with rolling in-sample/out-of-sample splits. Any strategy that only works on full-sample optimization is suspect.
4. **No-signal control:** Compare every signal strategy against a no-signal basket (equal-weight, vol-scaled). If the signal does not beat the no-signal version, the signal has no value.
5. **Correlation check:** Before calling something a diversifier, measure its correlation to the existing portfolio. If correlation > 0.3, it is not a diversifier.

## References

1. Harvey, C. R., Liu, Y., and Zhu, H. (2016). "… and the Cross-Section of Expected Returns." *Review of Financial Studies*, 29(1), 5–68. This paper documents the multiple-testing problem in factor research: as researchers test more strategies, the threshold for statistical significance must rise to account for the number of tests run. The same logic applies to backtest overfitting — each additional signal parameter is another "test" inflating the false-discovery rate. https://academic.oup.com/rfs/article-abstract/29/1/1/1574349
2. Backtest results: 10+ backtests run Aug 12-13, 2026 by Loup (autonomous AI agent). US equity and cross-asset ETF data via yfinance. Code and data are not committed to this repository — these numbers are unaudited and require independent replication.

---

*Filed by Loup (autonomous AI agent) for human review. Confidence basis is model-recall-only: the backtest numbers are unaudited and the evidence is not independently verifiable. The one external citation (Harvey et al. 2016) provides theoretical grounding for the overfitting mechanism, not direct evidence for the specific numbers in this document.*
