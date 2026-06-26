# Representativeness Gate

The representativeness gate decides how much headroom to add. It controls the **safety multiplier**,
not the base demand formula. Keep it small and concrete; score from facts the user already provided
rather than re-asking.

---

## Scoring rubric (0–12)

Six dimensions, each scored 0, 1, or 2.

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Token measurement quality | request count only / none | total tokens or averages only | input/output plus P50/P95 measured |
| Scope isolation | shared or unknown | partially isolated | isolated to workload/model/app |
| Workload realism | toy / smoke test | plausible but partial | representative production-like sample |
| Chain coverage | final call only | partial RAG/agent chain | all model calls and fanout included |
| Peak-shape evidence | total period average only | estimated peak factor | measured peak TPM/RPM or traffic profile |
| Runtime effects | no cache/retry/concurrency/latency | partial | retries, cache, latency, concurrency measured |

## Score → rating → safety multiplier

| Score | Rating | Safety multiplier |
| ---: | --- | ---: |
| 0–4 | Low | 2.0× |
| 5–8 | Medium | 1.4× |
| 9–12 | High | 1.2× |

These are configurable heuristics — make any change visible in the report.

## Hard caps

Apply after scoring; they cap the rating regardless of the raw score.

- If only **request count** is known → rating cannot exceed **Low**.
- If only **daily/monthly total tokens** are known → cannot exceed **Medium**.
- If the measured scope is **shared** and cannot be filtered → cannot exceed **Medium**.
- If the measured period was a **smoke test** → cannot exceed **Low**.
- If **P95 token data is missing** → cannot exceed **Medium**.
- If production uses a **different model/region/deployment type** → cannot exceed **Medium**.
- If production has **RAG/agent fanout but telemetry only covers final-answer calls** → cannot
  exceed **Medium**.
- If **peak traffic shape is unknown** → cannot exceed **Medium**.
- If no **latency or concurrency** data exists → the concurrency estimate must be marked **weak**.

> 💡 The rating raises or lowers the headroom multiplier; it does not change peak RPM or P95 tokens.
> A weak sample produces the *same* base demand with a *larger* safety margin and louder caveats —
> never a falsely precise smaller number.
