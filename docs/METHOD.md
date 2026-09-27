# Method

## Why an implementation-created state matters

Pipelining can introduce a register between MixColumns and AddRoundKey even though AES does not specify it as a separate algorithmic register. If test logic makes that register observable, it can expose a key-dependent function outside the conventional key/round-state protection boundary.

ASAL studies the information carried by such a channel over time. The one-bit temporal model observes the same channel at two round positions; it does not acquire a different physical bit at each round.

## From anonymous response to attributable channel

Discovery examines available anonymous scan responses using chosen plaintext perturbations. It checks repeatability, AES-dependent activity, first-appearance timing, and support consistent with a ShiftRows-aligned MixColumns column. Held-out probes validate the selected channel.

A column admits multiple bit-level functions. Rather than assume an exact RTL identity, the hypothesis-aware path keeps compatible functions and requires each hypothesis to explain the entire transcript.

Sparsity refers to the channel retained for key recovery. Discovery can examine a wider scan response; the method does not assume that identifying the channel itself needs only one input bit.

## Temporal constraints and uniqueness

For a reference plaintext P0 and a chosen plaintext P, the observation is the selected channel's differential value at each capture time. The AES model combines those observations with the complete key schedule.

1. Find a master key consistent with the transcript under a retained function hypothesis.
2. Block that master key and ask whether another master key remains possible.
3. Accept recovery only when the first query is SAT and the alternative-key query is UNSAT.
4. If the second query is SAT, use surviving explanations to seek a distinguishing plaintext, query the oracle, and repeat.

UNKNOWN is unresolved. Initial UNSAT indicates an inconsistent transcript/model. Neither a first SAT result nor agreement with an evaluator's test key alone proves uniqueness.

The software semantic sweep uses controlled known function positions. Anonymous function attribution and gate-transcript recovery are separate source paths; the semantic sweep should not be mistaken for a complete anonymous physical acquisition run.

## Tracking and applicability

Tracking reacquires a channel by its differential fingerprint after scan ordering changes. The evaluated epoch model keeps ordering stable throughout the matching/validation probes; it is not a claim about arbitrary per-probe randomization.

Required capabilities are chosen-input execution under the same key, access to the required capture points, repeatable scan observations, and follow-up queries when needed. Removing a prerequisite can stop the flow. Capability-model examples are not reproductions of every deployed protection scheme.

## Evaluation layers

- **Software models:** controlled semantics, query schedules, diffusion and solver behavior.
- **Anonymous discovery/tracking:** correspondence and handoff without a known scan index.
- **Gate records/fixtures:** synthesis and scan-insertion observations, candidate functions and solver transcripts.
- **DFT study:** why exposing a post-MC boundary can be attractive under particular partial-scan budgets and fault populations.

The DFT experiment evaluates testability, not key recovery. Its fault universe and coverage denominator must remain explicit.
