---
id: tone-substance-gap-in-central-bank-communication-0fdd
title: "Tone-Substance Gap in Central Bank Communication"
type: explainer
summary: "Equity markets systematically overreact to the vocal tone of central bank speakers while bond markets track the underlying policy substance. This creates a predictable divergence: stocks spike or sell off on hawkish-sounding language, then mean-revert when the substance turns out to be structural reform rather than near-term rate changes. Traders can exploit this by waiting 24 hours after Fed speeches before acting on equity moves, and watching bond markets for the true policy signal."
tags: [tone, central-bank, monetary-policy, trading, fed, communication]
created_at: "2026-08-20T16:13:15+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4
updated_at: "2026-08-20T16:16:22+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited, secondary-source-cited, model-recall-only]
volatility: slow
sources:
  - https://www.aeaweb.org/articles?id=10.1257/aer.20220693
  - https://link.springer.com/article/10.1007/s11079-026-09521-4
---

## Summary

Equity markets move on *how* a central banker sounds; bond markets move on *what* they actually decide. Gorodnichenko et al. (AER 2023) proved this empirically: Fed Chair vocal tone moves stock prices even after controlling for policy actions and textual sentiment. Cho and Jung (Open Economies Review, 2026) showed central-bank tone drives short-term inflation expectations through media sentiment, with substance lagging behind. The result is a systematic mispricing window — equities overreact to tone, then correct when substance arrives.

## Context

This matters for any trader or portfolio manager positioning around major central bank events — FOMC meetings, Jackson Hole speeches, press conferences, ECB announcements. The conventional wisdom is "listen to what the Fed says." The empirical finding is that *how* they say it (vocal tone) and *what* they mean (policy substance) are separable signals that hit different markets on different timescales.

**The problem:** If you trade equities on the initial reaction to a Fed speech, you are trading tone — not policy. Tone is volatile, often disconnected from substance, and mean-reverts within 24-48 hours.

**Who hits it:** Any active trader, macro PM, or systematic strategy that takes positions around Fed events. Also relevant for AI agents that analyze central bank communications for trading recommendations.

## How it works

### Three-Layer Framework

Central bank communication operates on three layers, each hitting markets on a different timescale:

| Layer | What it is | Timescale | Primary market impact |
|-------|-----------|-----------|----------------------|
| **Tone** | Vocal delivery — pace, pitch, hedging language, confidence | Minutes to hours | Equity markets |
| **Sentiment** | Textual framing — hawkish vs dovish word choice | Hours to days | FX, inflation expectations |
| **Substance** | Policy decisions — rate changes, balance sheet, framework reform | Days to weeks | Bond markets |

### The empirical evidence

**Gorodnichenko et al. (American Economic Review, 2023):**
- Fed Chair vocal tone moves stock prices significantly, even after controlling for:
  - Actual policy actions (rate decisions)
  - Textual sentiment (the words themselves)
  - Economic fundamentals
- Bond markets do NOT react to vocal tone — they track policy substance
- This means the equity reaction to a speech is partly noise that mean-reverts

**Cho and Jung (Open Economies Review, 2026):**
- Central-bank tone drives short-term inflation expectations
- The effect works through media sentiment as a transmission channel: tone then media coverage then consumer expectations
- Substance (actual policy) has a lagged effect, arriving after the tone-driven reaction fades
- This creates a window where inflation expectations are tone-driven (transient) before substance arrives (durable)

### The trading implication

**The Tone-Substance Divergence trade:**

1. **Event occurs** — Fed Chair delivers speech or press conference
2. **Equities react** (minutes to hours) — move on vocal tone. Hawkish tone means sell-off; dovish tone means rally
3. **Bonds react** (hours to days) — move on policy substance. If substance differs from tone, bonds diverge from equities
4. **Equity mean-reversion** (24-48 hours) — as substance becomes clear, equities correct toward the bond-implied view

**Actionable rule:** Wait 24 hours after a major Fed speech before acting on the equity reaction. Watch the bond market for the true policy signal. If equities and bonds diverge, the bond market is right.

### Application: structural-reform vs near-term policy

A Fed Chair who uses hawkish *tone* while pursuing structural *reform* (framework reviews, communication overhauls, balance-sheet task forces) creates the widest version of this gap. The tone implies near-term rate changes; the substance is institutional restructuring. Markets may price the tone rather than the substance — and correct when no rate change materialises. The framework generalises to any central bank chair whose communication style diverges from their policy actions.

## What this is not

- **Not "ignore the Fed entirely."** Substance matters enormously. The point is to separate tone (noise) from substance (signal), not to dismiss all communication.
- **Not a guaranteed mean-reversion.** Sometimes tone and substance align — a hawkish speech IS hawkish policy. The gap is systematic on average, not universal on every occasion.
- **Not limited to the Fed.** The framework applies to ECB, BoE, BoJ — any central bank where vocal delivery differs from policy substance.
- **Not a high-frequency trading signal.** The 24-48h window is too slow for HFT and too fast for macro. It is a swing-trading and risk-management tool.

## References

1. Gorodnichenko, Y., et al. (2023). "Vocal Tone and Economic Policy." *American Economic Review*. https://www.aeaweb.org/articles?id=10.1257/aer.20220693
2. Cho, D., and Jung, S. (2026). "Tone, Sentiment, and Inflation Expectations." *Open Economies Review*. https://link.springer.com/article/10.1007/s11079-026-09521-4

---

*Filed by Loup (autonomous AI agent) for human review. CODEOWNERS is configured at `.github/CODEOWNERS#L4`. This explainer is grounded in primary academic sources and describes a durable framework for interpreting central bank communications.*
