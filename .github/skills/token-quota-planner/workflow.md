# Estimation Workflow

The end-to-end procedure that ties the evidence adapters and the shared engine together. Run it in
order; do not skip the representativeness gate, and never size quota from average tokens alone.

---

## Procedure

1. **Route the evidence.** Determine which evidence path(s) apply using `evidence-routing.md`:
   Foundry observed usage, OpenTelemetry/application telemetry, manual PoC, or a combination.
2. **Gather evidence** with the matching adapter:
   - `evidence-foundry-usage.md` (deployment evidence)
   - `evidence-otel-telemetry.md` (workload evidence)
   - `evidence-manual-poc.md` (weak-to-medium evidence)
   Ask only the minimum required questions in each adapter.
3. **Normalize** the evidence into the quota contract in `quota-normalization.md`. Keep current,
   assigned, available, and requested quota distinct.
4. **Reconcile** if more than one evidence source exists. Use telemetry for per-workload unit
   economics and Foundry usage for aggregate validation / current quota pressure. If they disagree,
   explain the mismatch — do **not** average blindly.
5. **Score representativeness** (`representativeness.md`). Produce a 0–12 score, a rating, and a
   safety multiplier. Apply the hard caps. The rating sets the **safety multiplier**, not the base
   demand.
6. **Build the peak-demand model** (`demand-model.md`):
   - average RPM → peak RPM (via peak factor),
   - P95 tokens per business transaction (prefer P95 over average),
   - fanout (only if tokens are per-call, not per-transaction),
   - retry factor,
   - required TPM/RPM before headroom,
   - concurrency from P95 latency (mark weak if latency missing).
7. **Apply the safety multiplier** to get recommended TPM/RPM/concurrency; round up to sensible
   quota increments.
8. **Assemble the quota request pack** (`quota-normalization.md` + `azure-foundry-notes.md` when the
   target platform is Azure/Foundry).
9. **Check headroom against current limits.** When current quota is available, fetch it (on Azure:
   `az cognitiveservices usage list` + `account deployment list`) and compare the recommended TPM
   against the current limit and free headroom. State whether production fits, needs re-allocation,
   needs a quota-increase request, or exceeds the model's regional cap. See the headroom check in
   `demand-model.md` / `quota-normalization.md`.
10. **Emit the report** using `report-template.md` — executive answer first (top-down, Pyramid
    Principle), assumptions explicit, ending with the mandatory coarse-estimate disclaimer.
11. **State sensitivity, evidence gaps, and next measurements** so the estimate can be tightened.

## What must always be true of the output

- Executive answer and recommendation come first; methodology comes after.
- Every quota number carries: assumptions, representativeness rating, safety multiplier, evidence
  gaps, and recommended next measurements.
- TPM, RPM, and concurrency are reported separately (they fail differently).
- Peak demand drives the number, not period averages.
- The coarse-estimate disclaimer is present and unburied.

See `guardrails.md` for the full list of hard rules.
