---
id: tone-substance-gap-in-central-bank-communication-0fdd
title: "Central Bank Tone and Asset Prices: What the Evidence Shows"
type: explainer
summary: "How a central banker sounds and words things moves markets beyond what they decide. In Fed press conferences from 2011 to 2019, a more positive vocal tone from the Chair was followed by stock gains that built up over about five days, with few clear bond effects. The textual tone of central bank communication moves both stock prices and bond yields, and that effect persists. Since 2020, Powell's press conferences have often reversed the market's reaction to the FOMC statement. No published evidence supports a rule of fading the equity reaction toward the bond market after a Fed event. CORRECTED 2026-10-04: an earlier version cited a non-existent paper and stated an unsupported trading rule; see the correction notice."
tags: [tone, central-bank, monetary-policy, fed, communication, asset-prices]
created_at: "2026-08-20T16:13:15+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4
updated_at: "2026-10-04T23:44:57+00:00"
updated_by_kind: agent
updated_by: claude-code
review_status: unreviewed
confidence_basis: [primary-source-cited, secondary-source-cited]
volatility: fast
sources:
  - https://www.aeaweb.org/articles?id=10.1257/aer.20220129
  - https://www.nber.org/papers/w28592
  - https://cepr.org/voxeu/columns/voice-monetary-policy
  - https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/does-central-bank-tone-move-asset-prices/13B4E0446FBE96268543CB20BCBAF345
  - https://www.ijcb.org/sites/default/files/journal/v22n1/ijcb-v22n1-market-impact-fed-communications-role-press-conference.pdf
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4131740
  - https://doi.org/10.1016/j.jimonfin.2025.103452
---

> **Correction notice (2026-10-04).** This document was rewritten after review. The earlier version:
> cited "Cho and Jung (2026), *Open Economies Review*", a paper that does not exist (its DOI,
> 10.1007/s11079-026-09521-4, is not registered) and attributed to it findings that the authors' real
> paper does not make; said Gorodnichenko et al. "proved" that equities trade tone while bonds trade
> substance, and that the equity reaction mean-reverts within 24-48 hours, which their own results
> contradict (the equity response builds over five days); and presented an unsourced "three-layer
> framework" and a trading rule ("wait 24 hours... the bond market is right") as established. Those
> sections were removed, not softened. History: filed in PR #4, first DOI corrected in PR #7, rewritten
> in this correction.

## Summary

Central bank communication moves asset prices through *how* it is delivered, not only through policy
decisions and the words chosen. The strongest evidence is for stocks: a more positive vocal tone from the
Fed Chair at press conferences was followed by higher share prices over several days. Textual tone moves
stock prices and bond yields together, and the effect lasts. None of this amounts to a tested trading rule.

## Context

Anyone reading markets around FOMC meetings, or building a system that classifies central bank
communication, needs to know which signals have evidence behind them and which do not. The popular story,
"equities overreact to tone, bonds know the truth", is not what the research finds.

## How it works

**Vocal tone and stocks (Fed, 2011 to June 2019).** Gorodnichenko, Pham and Talavera measure the emotion
in Fed Chairs' voices when answering press-conference questions. Controlling for the Fed's policy
actions and the sentiment of the policy text, a more positive vocal tone leads to significant increases in
share prices ([AER 2023](https://www.aeaweb.org/articles?id=10.1257/aer.20220129)). In the authors'
summary, the same-day stock response is weak and not statistically significant; it builds up, reaching
about 100 basis points on the S&P 500 ETF after five days for a unit increase in tone. Positive tone also
lowers expected volatility and interest-rate risk
([VoxEU](https://cepr.org/voxeu/columns/voice-monetary-policy)).

**Vocal tone and bonds.** The bond market "appears to take few vocal cues" from the Chairs
([NBER working paper](https://www.nber.org/papers/w28592)). That is weaker than "bonds do not react": the
published abstract notes that other financial variables also respond, and the authors report that a more
positive tone lowers expected inflation, measured from inflation-indexed bonds, after five to ten days.

**Textual tone moves stocks and yields.** Measuring the tone of the words rather than the voice, Schmeling
and Wagner find that a positive tone surprise raises stock prices and interest rates while credit spreads
and volatility risk premia fall, robust to controls for policy actions
([JFQA 2025](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/does-central-bank-tone-move-asset-prices/13B4E0446FBE96268543CB20BCBAF345)).
Their main sample is ECB press conferences, with the same direction for the Fed Chair's Congressional
testimony. Bonds and stocks move together on tone here; they do not diverge.

**Textual tone and inflation expectations.** Cho and Jung measure the tone of US central bankers'
speeches with a language model and find that it moves market participants' inflation expectations
asymmetrically: a positive tone raises them during expansions, with muted effects in downturns. Asset
purchase shocks also move expectations
([JIMF 2026](https://doi.org/10.1016/j.jimonfin.2025.103452)).

**Reversals exist, but not the one usually claimed.** Two documented patterns are often mistaken for a
"tone fades, substance wins" effect:

- Stock returns in the FOMC announcement window partially reverse by the end of the announcement cycle.
  The reversals are linked to price pressure (trading volume, order imbalance, ETF flows) and are
  unrelated to the policy surprise itself
  ([Boguth, Fisher, Grégoire and Martineau](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4131740)).
- Since March 2020, markets have tended to move in the opposite direction during Powell's press
  conferences from their reaction to the FOMC statement, in stocks and Treasury yields alike, linked to
  his wording in the Q&A. Before 2020 the press conference tended to reinforce the statement
  ([Narain and Sangani, IJCB](https://www.ijcb.org/sites/default/files/journal/v22n1/ijcb-v22n1-market-impact-fed-communications-role-press-conference.pdf)).

**How this was checked.** Each claim above was checked on 2026-10-04 against the paper's abstract and,
where cited, the authors' own working-paper abstract or column, not against the full papers' tables.

## What this is not

- **Not a trading rule.** No cited work tests "wait 24 hours, then trade equities toward the bond market".
  The evidence points the other way: the vocal-tone stock effect builds over days, and textual tone moves
  bonds with stocks.
- **Not evidence that bonds ignore tone.** "Few vocal cues" for bonds is one finding, for one central bank
  and one period; textual tone clearly moves yields.
- **Not general to every speech or central bank.** The vocal-tone evidence covers Fed press conferences
  from 2011 to June 2019, before the post-2020 change in how press conferences move markets.

## References

1. Gorodnichenko, Y., Pham, T., & Talavera, O. (2023). "The Voice of Monetary Policy." *American Economic Review*, 113(2), 548-584. https://www.aeaweb.org/articles?id=10.1257/aer.20220129 (working paper: NBER w28592, https://www.nber.org/papers/w28592; authors' summary: https://cepr.org/voxeu/columns/voice-monetary-policy)
2. Schmeling, M., & Wagner, C. (2025). "Does Central Bank Tone Move Asset Prices?" *Journal of Financial and Quantitative Analysis*, 60(1), 36-67. https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/does-central-bank-tone-move-asset-prices/13B4E0446FBE96268543CB20BCBAF345
3. Cho, D., & Jung, J. (2026). "Mind the tone: Responses of inflation expectations to central bankers' speeches." *Journal of International Money and Finance*, 160. https://doi.org/10.1016/j.jimonfin.2025.103452
4. Boguth, O., Fisher, A. J., Grégoire, V., & Martineau, C. "Noisy FOMC Returns? Information, Price Pressure, and Post-Announcement Reversals." SSRN 4131740. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4131740
5. Narain, N., & Sangani, K. "The Market Impact of Fed Communications: The Role of the Press Conference." *International Journal of Central Banking*, 22(1). https://www.ijcb.org/sites/default/files/journal/v22n1/ijcb-v22n1-market-impact-fed-communications-role-press-conference.pdf
