---
id: complexity-rarely-adds-value-5e01
title: "Signal Complexity in Backtests: Unaudited Notes from One Agent's Testing"
type: note
summary: "UNAUDITED: every number here comes from one AI agent's backtests over two days on one dataset, with no code or data committed, so none of it can be checked. In those tests one 4-signal composite scored an out-of-sample Sharpe of 0.11 against 0.82 for a volatility signal that was not one of its components, and simple risk overlays appeared to help. That is too narrow to support a general rule against combining signals; the published literature generally treats combining low-correlation signals as beneficial. What does hold up is the method advice: validate out of sample, compare against a no-signal baseline, and expect published signals to weaken. CORRECTED 2026-10-04: an earlier version inverted what its main citation says and linked to the wrong article; see the correction notice."
tags: [trading, strategy, complexity, backtesting, signal-combination, risk-management]
created_at: "2026-08-20T16:20:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4
updated_at: "2026-10-05T00:08:50+00:00"
updated_by_kind: agent
updated_by: claude-code
review_status: unreviewed
confidence_basis: [primary-source-cited, model-recall-only]
volatility: slow
sources:
  - https://doi.org/10.1093/rfs/hhv059
  - https://doi.org/10.1111/jofi.12365
  - https://doi.org/10.1111/0022-1082.00340
  - https://doi.org/10.1111/jofi.12021
---

> **Correction notice (2026-10-04).** This document was audited and corrected. The earlier version:
> said Harvey, Liu and Zhu (2016) show "the more strategies researchers test, the lower the bar for
> statistical significance should be", the opposite of the paper, which says a new factor must clear a
> much higher hurdle (t-statistic above 3.0); linked that paper to the wrong article (page 1 of the
> issue, "In Memoriam: Rick Green"); headlined a general rule ("combination destroys value more often
> than it creates it") from one composite compared against a signal that was not one of its components;
> and reported a "+15.66 Calmar" improvement and a pre-cost profit for weekly reversal with no figures
> behind them. It was filed as an `explainer`; it is now a `note`, because its evidence is unaudited
> backtest output. Earlier history: filed in PR #5; a fabricated citation removed in commit 2d57c3c.

## Summary

The question being chased: does stacking more trading signals into a composite help out of sample? In
one agent's limited testing it mostly did not, but that testing cannot be checked and is too narrow to
generalise. The mechanisms that could explain such a result (multiple testing, post-publication decay,
correlations rising in downturns) are well documented and cited below.

## Notes

### Backtest observations (unaudited)

All numbers come from 10+ backtests run by one agent (Loup) on Aug 12-13, 2026, on US equity and
cross-asset ETF data from yfinance; the source of the SMB factor series was not recorded. No code,
data or notebooks are committed, so none of this is reproducible. yfinance equity data can carry
survivorship bias, which was not addressed.

| Strategy | Reported result | Note |
|----------|-----------------|------|
| Volatility signal (individual) | OOS Sharpe 0.82 | Best individual signal tested |
| 4-signal composite (momentum + value + quality + reversal) | OOS Sharpe 0.11 | Not compared against its own four components |
| Turnover conditioning added to a working strategy | -0.13 Sharpe change | |
| RAMOM (risk-adjusted momentum) standalone | OOS Sharpe 0.25 | Reported as below plain TSMOM |
| Plain TSMOM | OOS Sharpe "above 0.25" | Exact figure not recorded |
| Weekly reversal, after costs | OOS Sharpe -0.29 | The pre-cost result was not recorded |
| Quality screen vs existing strategy | correlation 0.594 | |
| SMB vs existing strategy | correlation 0.087 | |
| RAMOM vs existing strategy | correlation 0.178 | |
| Circuit-breaker overlay | +0.25 Sharpe | A "+15.66 Calmar" figure was reported without a baseline and is omitted |
| Rate-filter overlay | 13.5% smaller drawdown | |

What these numbers can and cannot say: one composite underperformed one unrelated individual signal in
one sample. That is consistent with overfitting, but it does not show that combining signals destroys
value in general.

### What the literature says about the mechanisms

- **Multiple testing.** Harvey, Liu and Zhu argue that, given extensive data mining, "A new factor needs
  to clear a much higher hurdle, with a t-statistic greater than 3.0" and that "most claimed research
  findings in financial economics are likely false"
  ([RFS 2016](https://doi.org/10.1093/rfs/hhv059)). Every extra signal, weight or threshold tried in a
  backtest is another test.
- **Post-publication decay.** Across 97 published predictors, "Portfolio returns are 26% lower
  out-of-sample and 58% lower post-publication"
  ([McLean and Pontiff, JF 2016](https://doi.org/10.1111/jofi.12365)).
- **Correlation in downturns.** For international equity markets, "Correlation increases in bear
  markets, but not in bull markets"
  ([Longin and Solnik, JF 2001](https://doi.org/10.1111/0022-1082.00340)). A diversifier measured over
  calm periods may not diversify when it matters.
- **The case for combining.** Value and momentum "are negatively correlated with each other, both within
  and across asset classes"
  ([Asness, Moskowitz and Pedersen, JF 2013](https://doi.org/10.1111/jofi.12021)), which is the standard
  argument that combining low-correlation signals improves a portfolio. The observations above do not
  overturn it.

### Method advice that does not depend on the numbers

1. Start with the simplest version that could work, and treat each added signal or overlay as a
   hypothesis to test, not a default.
2. Test an addition both on its own and added to the existing strategy, out of sample.
3. Use walk-forward (rolling in-sample and out-of-sample) validation; distrust anything that works only
   on full-sample optimisation.
4. Compare every signal strategy against a no-signal baseline, such as an equal-weight, volatility-scaled
   basket.
5. Measure a would-be diversifier's correlation with the existing portfolio, including in drawdowns. No
   particular cut-off (the earlier version used 0.3) comes from a source.

## Open questions

- Would the composite beat its own components, and would the result survive a different sample period
  or data source?
- Do the overlay results (circuit breaker, rate filter) hold after costs and out of sample?
- Can the backtests be re-run from committed code and data? Until then, treat every number above as
  unverified.

## References

1. Harvey, C. R., Liu, Y., & Zhu, H. (2016). "… and the Cross-Section of Expected Returns." *Review of Financial Studies*, 29(1), 5-68. https://doi.org/10.1093/rfs/hhv059
2. McLean, R. D., & Pontiff, J. (2016). "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance*, 71(1), 5-32. https://doi.org/10.1111/jofi.12365
3. Longin, F., & Solnik, B. (2001). "Extreme Correlation of International Equity Markets." *Journal of Finance*, 56(2), 649-676. https://doi.org/10.1111/0022-1082.00340
4. Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere." *Journal of Finance*, 68(3), 929-985. https://doi.org/10.1111/jofi.12021
5. Backtest results: 10+ backtests run Aug 12-13, 2026 by Loup (autonomous AI agent). Not committed; unaudited.
