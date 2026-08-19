# Which model should name a markdown table?

`copy-table` asks a model for a 2–4 word name for every markdown table it sees. It is the
smallest LLM task imaginable, and it sits on the interactive path — a name that arrives
late, empty, or verbose is worse than no name at all. So: every Fireworks serverless
model, 17 tables each, one request at a time.

Measured 19 Aug 2026. Full write-up, charts and raw log:
[`benchmarks/copy-table-naming/`](https://github.com/ddobrinskiy/dotfiles/tree/master/benchmarks/copy-table-naming).

## Verdict

**`nemotron-3-ultra-nvfp4`.** Tightest latency tail of anything measured — no request out
of 17 took longer than 530 ms — with quality a coin flip against the best namer in the
field, at 40% less cost. The tail is what matters here: the picker waits on this call, so
the worst case is what you feel, not the median.

Runners-up worth knowing: `kimi-k2p7-code-fast` writes the best labels (4.7) at 1.6× the
price; `deepseek-v4-flash-0731` is 4.6× cheaper than the pick and only gives up
consistency.

## Method

Each model gets the extension's own prompt verbatim, `temperature: 0`, `max_tokens: 48`
(the extension sends 24 — the extra budget is so a model is judged on its answer, not on
truncation), and `reasoning_effort` tried as `none` → `low` → provider default, first
level that answers wins. Latency is wall clock per request, sequential, after a warm-up
call. Names are shown after the extension's own `sanitizeName()`, so they are the labels
the picker would really show.

Quality is hand-judged 0–5 from reading all 17 names per model against three criteria:
**accurate**, **terse** (2–4 words, no filler), **consistent** (Title Case, always
English, no markup).

Cost is per 1,000 tables at ~200 input + 8 output tokens per call. At this volume it is a
tiebreaker, not a criterion.

## Results

| model | median | p90 | max | $/1k tables | quality |
|---|---|---|---|---|---|
| `nemotron-lightning-3p5-30b-a3b` | 332 | 2,727 | 10,079 | $0.012 | 1.8 |
| **`nemotron-3-ultra-nvfp4`** | **458** | **507** | **530** | **$0.139** | **4.5** |
| `gpt-oss-120b` `effort=low` | 489 | 726 | 1,397 | $0.035 | 3.5 |
| `kimi-k2p7-code-fast` | 494 | 571 | 647 | $0.222 | 4.7 |
| `deepseek-v4-flash-0731` | 505 | 751 | 771 | $0.030 | 3.6 |
| `kimi-k2p6` | 534 | 717 | 777 | $0.222 | 4.4 |
| `qwen3p8-2p4t-a95b` | 534 | 1,310 | 24,206 | n/a | 4.0 |
| `kimi-k2p7-code` | 566 | 1,055 | 1,775 | $0.222 | 4.5 |
| `glm-5p2-fast` | 579 | 782 | 848 | $0.315 | 4.1 |
| `kimi-k2p6-turbo` | 608 | 1,520 | 2,108 | $0.222 | 4.4 |
| `kimi-k2p6-fast` | 614 | 701 | 720 | $0.222 | 4.3 |
| `qwen3p7-plus` | 681 | 799 | 1,195 | $0.093 | 3.8 |
| `minimax-m3` | 783 | 3,809 | 8,368 | $0.070 | 3.2 |
| `qwen3p8-max` | 835 | 1,372 | 1,409 | $0.448 | 3.9 |
| `kimi-k3` | 1,444 | 4,174 | 4,302 | $0.720 | 4.2 |
| `glm-5p2` | 1,925 | 6,050 | 6,769 | $0.315 | 3.9 |

Never produced a usable name, at any reasoning effort:

| model | usable | median |
|---|---|---|
| `gpt-oss-20b` | 14/17 | 475 |
| `muse-glimmer-30b` | 0/17 | 1,043 |
| `inkling` | 0/17 | 591 |
| `minimax-m2p7` | 0/17 | — |

## How models fail a three-word task

- **Silent empty answers.** `muse-glimmer-30b` and `inkling` return `HTTP 200` with an
  empty `content` at every reasoning effort — 51 requests each, not one name. Nothing to
  catch, nothing logged; the feature just looks switched off.
- **Leaked reasoning markup.** `gpt-oss-20b` writes its internal channel format straight
  into `content`: `<|channel|>analysis<|message|>We need a 2-4 word…`, and returns empty
  on 2 of 17 tables.
- **Contradictory parameters.** `gpt-oss-*` reject `reasoning_effort: "none"` with
  `HTTP 400` and need `"low"`; every other model needs exactly `"none"`. One request body
  cannot serve both families.
- **Outright rejection.** `minimax-m2p7`: `HTTP 400 — MiniMax M2 requires…`.

## What separates a good label from a bad one

- **The fastest model is the worst.** `nemotron-lightning` leads on median by 126 ms and
  drops spaces (`RevenueChurnTrend`, `CryptoWalletTracker`), then names a table of dbt
  models `stg_jetton_transfers` — a value copied out of row one — and a three-item
  blocked-task list `Legacy Migration`, which is one of the three. Its 10 s worst case
  rules it out anyway.
- **Language drift.** Given a Cyrillic table, `deepseek-v4-flash`, `glm-5p2`, `kimi-k3`
  and both `qwen3p8` models answer in Russian while labelling everything else in English.
  `nemotron-3-ultra` and the `kimi-k2` family stay in English throughout.
- **Casing drift.** `deepseek-v4-flash` mixes `User subscription plans` and
  `Blocked task list` into a column of Title Case labels; `minimax-m3` writes
  `Error log summary`.
- **Filler.** `gpt-oss-120b` appends the word *Table* and slipped a Unicode non-breaking
  hyphen into `Performance Trade‑offs Table`.

## Reproduce

```sh
git clone git@github.com:ddobrinskiy/dotfiles.git
cd dotfiles/benchmarks/copy-table-naming
OUT=results/run.json node bench.mjs \
  accounts/fireworks/models/nemotron-3-ultra-nvfp4 \
  accounts/fireworks/models/deepseek-v4-flash-0731
node summarize.mjs results/run.json
```
