# Late 1-Bit Dependency-Guided Adaptive Campaign Design

Date: 2026-07-17

Status: approved experiment design. This document defines the campaign but does
not itself authorize a recovery claim before the implementation and result
checks pass.

## 1. Objective

Test whether one fixed scan-visible late-class 1-bit FF can uniquely identify
the AES-128 master key when the attacker has an exact, noiseless,
chosen-plaintext differential oracle and may issue adaptive queries without an
artificial query or solver-time limit.

The experiment asks a narrower question than the earlier 2/3/4-bit sweeps:

> For a fixed single `MC` or `ARK` semantic bit observed over the modeled two
> rounds, can residual-key-aware adaptive queries reduce the exact key set to
> one key, or can the oracle be proved unable to separate a residual key pair?

One FF means exactly one 1-bit flip-flop. The 128-bit semantic surfaces are
reference maps for selecting that one function, not observable register banks.

## 2. Inherited Threat Model

- Unknown secret: AES-128 master key `K0`.
- Cipher: the same standard AES-128 model, key schedule, state indexing, and
  two-round temporal observation model used by Phase 7 and Phase 8.
- Oracle: exact and noiseless chosen-plaintext leakage.
- Mapping: stage, bit index, round, and cycle are known exactly.
- Tap budget: one fixed 1-bit FF for the entire attack run.
- Observation mode: differential against the same fixed reference plaintext
  convention used by Phase 8.
- Query policy: each plaintext may depend on the complete prior transcript.
- Query accounting: the initial transcript and every adaptive oracle call must
  be logged separately.

Changing the observed bit between queries is prohibited. Such a run would no
longer be a 1-bit fixed-tap attack.

## 3. Why This Experiment Is Not Already Decided

Earlier first-round relational experiments showed that one late bit could expose
strong local information, including four whitening-key bytes, but did not prove
full `K0` recovery. This campaign observes the same fixed bit temporally over two
rounds and uses adaptive chosen plaintexts, so the old local result is evidence,
not a terminal answer.

For a late bit at round 1, conservative structural provenance reaches 32 `K0`
bits. At round 2 it reaches all 128 `K0` bits. Therefore every selected tap is
structurally support-complete over the two-round signature. That is only a
necessary information-flow condition. It does not prove injectivity of the
oracle signature and must not be reported as recovery.

With one bit observed in each of two rounds, one query returns at most two
leakage bits. An information-counting lower bound is therefore approximately 64
independent queries for a 128-bit key. Correlation and redundant observations can
make the actual requirement much larger.

## 4. Position Sampling

The campaign uses 32 single-tap positions: 16 `MC` bits and 16 `ARK` bits.
There is one `MC` and one `ARK` sample in every AES state byte. Bit offsets are
balanced, and the `MC` and `ARK` samples in a byte differ by four bit lanes.

```text
MC:  0, 9, 18, 27, 36, 45, 54, 63,
     64, 73, 82, 91, 100, 109, 118, 127

ARK: 4, 13, 22, 31, 32, 41, 50, 59,
     68, 77, 86, 95, 96, 105, 114, 123
```

Equivalently, for state byte `b` in `0..15`:

```text
MC index  = 8*b + (b mod 8)
ARK index = 8*b + ((b + 4) mod 8)
```

This construction has four properties:

1. All 16 state bytes are represented at both late stages.
2. Every bit-in-byte lane appears twice within each stage.
3. The two stage samples cover disjoint semantic bit indices.
4. It avoids pairing `MC_i` with `ARK_i`, which would duplicate a differential
   leakage class because the round-key XOR cancels in the differential trace.

The 32 positions are a balanced sample, not an exhaustive statement about all
256 late semantic candidates.

## 5. Replication and Scheduling

- Key/query seeds per tap: 3.
- Seed identifiers: `0`, `1`, and `2`, unless the inherited deterministic seed
  API requires an equivalent explicit mapping.
- Total independent runs: `32 positions * 3 seeds = 96`.
- Maximum concurrent workers: 32.
- Scheduler: bounded worker pool, not 96 independently spawned solvers.
- Launch mode: detached `setsid` shell launcher with PID and campaign log.
- Resume: each run checkpoints after every accepted oracle observation.

A position-level recovery claim requires all three runs to have a proof-backed
terminal result. Per-seed results remain visible; they must not be collapsed by
topology consensus.

### 5.1 Bootstrap transcript

Each run starts with the inherited deterministic fixed-query generator at
`q64`. This matches the two-leakage-bits-per-query information lower bound while
providing a reproducible pre-adaptive baseline. The hidden key and query stream
seeds must be stored as separate fields even if the inherited seed API derives
both from one run seed.

Immediately after loading the 64 oracle observations, run the exact first and
second key solves:

- second-solve UNSAT: record `FIXED_Q64_RECOVERED`; do not attribute this result
  to the adaptive or dependency-guided algorithm;
- second-solve SAT: retain both models and enter the adaptive loop;
- UNKNOWN: checkpoint and retry; do not enter the adaptive loop with an
  unclassified bootstrap transcript.

The adaptive query counter starts at zero after the fixed `q64` transcript.
Reports must show both `total_query_count = 64 + adaptive_query_count` and the
adaptive count alone.

## 6. Exact Leakage Signature

For fixed tap `t`, reference plaintext `P0`, query plaintext `P`, key `K`, and
observed rounds `R = {1, 2}`, define:

```text
D[t,r](P,P0,K) = F[t,r](P,K) XOR F[t,r](P0,K)
G_t(P,K) = [D[t,1](P,P0,K), D[t,2](P,P0,K)]
```

After queries `P_1 ... P_n` and oracle observations `Y_1 ... Y_n`:

```text
C_n(K) = AND_i (G_t(P_i,K) = Y_i)
```

All key recovery and non-recovery decisions are made against `C_n`, not against
a sampled candidate-key pool or a dependency score.

## 7. Dependency-Guided Adaptive Attack

### 7.1 Exact candidate and alternative-key solves

At each step:

```text
SAT(C_n(K)) -> K_star
SAT(C_n(K) AND K != K_star) -> at least one alternative key
```

When practical, enumerate a bounded diverse pool of transcript-consistent keys
by adding model-blocking constraints. The pool is used only to choose a useful
next query. Pool exhaustion does not prove uniqueness; the exact second solve
does.

### 7.2 Residual dependency state

For the candidate pool `H_n`, compute the unresolved master-key bits:

```text
U_n = { j : there exist K_a,K_b in H_n with K_a[j] != K_b[j] }
```

Static structural support is retained as an admissibility check and diagnostic.
Because round-2 late support is expected to include all 128 bits, useful dynamic
guidance must come from functional activity rather than support membership alone.

For plaintext `P`, estimate the active Boolean influence of unresolved bit `j`
over the pool:

```text
I_j(P) = sum over K in H_n of
         [G_t(P,K) != G_t(P,K XOR e_j)]
```

These evaluations use the exact concrete AES/leakage implementation. A flipped
key need not satisfy the current transcript because `I_j` is a query-selection
sensitivity diagnostic, not a candidate-key assertion.

### 7.3 Distinguishing plaintext generation

Generate plaintext candidates with exact AES miters. For selected distinct
`K_a,K_b` in the candidate pool, solve:

```text
G_t(P,K_a) != G_t(P,K_b)
```

Collect multiple models by blocking previously generated plaintexts. Candidate
pairs should include keys with diverse unresolved-key difference patterns, not
only the first two solver models.

If a selected pair has no separator, invoke the global joint miter before making
any non-recovery decision. Pairwise non-separability alone does not prove that
the complete residual key class is non-separable.

### 7.4 Query scoring

For each generated plaintext, simulate `G_t(P,K)` for all `K` in the bounded
candidate pool and rank it lexicographically by:

1. maximum reduction of the largest leakage-signature bucket;
2. higher partition entropy over the possible two-bit signatures;
3. larger and more balanced active influence across `U_n`;
4. lower overlap with dependency-activity patterns of prior queries;
5. deterministic plaintext order as the final tie-breaker.

The primary partition terms prevent a high sensitivity count from winning when
it does not separate current candidates. Dependency influence is a secondary
criterion that favors queries exercising unresolved parts of `K0`.

The scoring constants, pool size, number of candidate pairs, and number of
plaintext models per pair must be fixed in configuration and logged. They may
affect efficiency but never the soundness of the final verdict.

### 7.5 Oracle update

Issue only the highest-ranked plaintext to the hidden-key oracle, append the
exact two-round leakage to `C_n`, persist the checkpoint, and repeat.

## 8. Proof-Backed Terminal Outcomes

### 8.1 Recovered

```text
SAT(C_n(K)) -> K_star
UNSAT(C_n(K) AND K != K_star)
```

Only this `SAT -> UNSAT` sequence is full-key recovery.

### 8.2 Proven non-recoverable for the fixed oracle

If an alternative key remains, solve a global separator formula containing two
distinct transcript-consistent keys and one new plaintext:

```text
C_n(K_a)
AND C_n(K_b)
AND K_a != K_b
AND G_t(P,K_a) != G_t(P,K_b)
```

If this formula is UNSAT, the residual ambiguity is observationally
non-separable under the fixed 1-bit, two-round differential oracle. Record the
run as `PROVEN_NONRECOVERABLE`, not merely `AMBIGUOUS`.

### 8.3 Still running

`UNKNOWN`, solver interruption, resource failure, or an incomplete miter is not
a scientific verdict. Checkpoint and retry with the configured solver portfolio.
There is no finite query-count or solver-time cutoff that converts such a state
to attack failure.

The absence of a limit does not guarantee termination. Runs without a proof
remain explicitly nonterminal.

## 9. Soundness Boundaries

- Candidate-pool entropy and influence are heuristics only.
- Structural or dynamic support completeness is not uniqueness.
- One pair having no distinguishing plaintext is not global non-separability.
- A recovered seed does not substitute for an unfinished seed.
- `MC_i` and `ARK_i` differential equivalence must be preserved in analysis.
- Results apply directly only to physically implemented FFs proven functionally
  and temporally equivalent to the selected clean semantic bits.
- Internal, fused, partial-XOR, or retimed functions require new Boolean cones
  and cannot inherit these results from a name or approximate location.

## 10. Required Artifacts

The implementation must produce:

- a machine-readable 32-position manifest;
- a 96-run campaign manifest including seeds and deterministic run IDs;
- a configuration recording all candidate-pool and query-scoring parameters;
- per-run checkpoints containing transcript, candidate models, chosen query,
  score components, solver status, and elapsed times;
- detached-launch PID and combined scheduler log;
- one JSONL summary row per run;
- a position-level aggregate that keeps all three seed verdicts visible;
- separate counts for fixed bootstrap recovery and post-bootstrap adaptive
  recovery;
- regression tests for tap invariance, MC/ARK differential equivalence,
  scoring determinism, resume behavior, exact uniqueness, and global
  non-separability.

## 11. Interpretation Matrix

The campaign supports only the following claim levels:

| Evidence | Permitted interpretation |
|---|---|
| One recovered seed | Existence proof for that exact tap and seed |
| Three recovered seeds at one tap | Replicated empirical recovery at that tap |
| Broad recovery across sampled MC/ARK taps | Evidence that adaptive 1-bit late leakage is a high-risk sampled class |
| All 96 runs recovered | Recovery across this balanced sample, not all 256 positions or all keys |
| Global miter UNSAT | Proven non-recovery for that exact tap, transcript model, and oracle definition |
| UNKNOWN or unfinished | No conclusion |

The main report must separate the effect of adaptive query growth from the
effect of dependency-guided ranking. At minimum, log whether the chosen query
would have been the first unscored pairwise-miter model and report the influence
and partition scores. A later baseline ablation can compare query counts, but
the recovery proof itself remains exact in both cases.

## 12. Pre-Launch Acceptance Checks

Before launching 32 workers:

1. Confirm all 32 indices exist in the inherited candidate map.
2. Confirm each run contains exactly one immutable tap.
3. Confirm MC and ARK selected index sets are disjoint.
4. Confirm each tap has expected round-1 and round-2 support metadata.
5. Confirm the differential `MC_i == ARK_i` identity with regression tests.
6. Confirm a tiny known-key fixture reaches exact uniqueness.
7. Confirm a synthetic non-separable fixture reaches global-miter UNSAT.
8. Confirm UNKNOWN is retried and never serialized as success or failure.
9. Confirm checkpoint resume does not repeat an oracle query.
10. Confirm the worker pool never exceeds 32 live run workers.
11. Confirm fixed `q64` recovery is not labeled adaptive recovery.

Only after these checks pass should the detached 96-run campaign start.
