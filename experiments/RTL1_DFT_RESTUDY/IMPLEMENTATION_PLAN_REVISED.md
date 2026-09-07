# AES-Internal D1-D5 Implementation Plan, Revision 2

This plan supersedes the earlier host-only-common plan.
No DFT/TetraMAX result generated from the earlier candidate manifests is valid for revision 2.

## 1. Freeze the functional checkpoint

- Use the existing one-round `mor1kx_aes_soc` pre-DFT DDC and Verilog.
- Recompute and record both checkpoint hashes.
- Confirm AES inventory: 772 FF; four stage banks of 128; key/plaintext and
  valid/done controls present.
- Do not change RTL, synthesis, libraries, constraints, or functional protocol.

## 2. Rebuild the fair scan groups

- Restore the existing 896-entry common set as the starting point.
- Assert that all 128 `key_reg` and 128 `plaintext_reg` cells are common, along
  with the AES transaction control cells.
- Preserve the other common host cells; do not replace AES input cells with host
  cells merely to create a random pool.
- Create `CASE_IARK`, `CASE_SB`, `CASE_SR`, and `CASE_MC` with exactly one
  128-cell stage bank added to the fixed common set.
- Create ten `RANDOM_STAGE_seedNN` lists by sampling 128 cells from the union
  of all 512 stage FFs. Record bank composition for every seed.
- Create nested `MIX_MC_000/032/064/096/128` lists with total variable count
  fixed at 128.
- Create `AUTO_STAGE` from the full 512-stage candidate universe using a
  deterministic, ATPG-independent structural ranking.

## 3. Verify functional serial continuity

- Parse the pre-DFT graph and check the data path
  `key/plaintext -> IARK -> SB -> SR -> MC`.
- Stop traversal at sequential boundaries; do not traverse CP/CD/scan-enable as
  data inputs.
- Emit a connectivity report containing each stage D driver, predecessor
  boundary, missing-driver count, and scan-disabled functional equivalence
  result.
- Mark the campaign `INVALID` if the path is cut or if input control is absent.

## 4. Build one common AES fault universe

- Start from the same checkpoint-derived valid fault source for every case.
- Keep all valid AES-internal combinational sites, including S-Box, IARK,
  ShiftRows, and MixColumns logic.
- Remove AES output interface sites, host/interface sites, scan-only sites, and
  all Q/QN direct fault sites of all 772 AES FFs.
- Generate the same site universe for stuck-at and transition polarity lists.
- Generate a separate collapsed source through a real collapse step. Never use
  `historical_canonical_faults_422.list` as a substitute.

## 5. Run DFT insertion

- Branch every case from the same pre-DFT checkpoint.
- Use the same 896 common cells and one 128-cell variable list.
- Use one chain of 1,024 cells and identical scan protocol.
- Run DRC before and after insertion.
- Verify input common membership, scan count, chain count, checkpoint hash, and
  post-DFT functional equivalence before ATPG.

## 6. Run ATPG

- Run stuck-at for all primary stage, random-stage, mix, and auto cases.
- Run transition with the same source-site universe and a fixed launch/capture
  protocol.
- Keep separate raw/collapsed result namespaces.
- Preserve summary, detailed fault status, patterns, runtime, AU/UD/ND, and all
  DRC/protocol warnings.
- Never convert timeout, abort, or UNKNOWN to detected or undetected.

## 7. Analyze D1-D5

- D1: compare direct-excluded residual detection against the common-only
  diagnostic and stage/random controls.
- D2: report stage matrix, random seed distribution, and MC-fraction sweep.
- D3: classify every accepted site into IARK/SB/SR/MC cone, control, other,
  overlap, or unresolved; report status transitions by region.
- D4: compare stuck-at and transition results without mixing denominators.
- D5: report automatic ranking composition and coverage; do not call it a
  commercial partial-scan ranking.

## 8. Validity gate

The final report may contain a comparative claim only when all of the following
are identical across cases:

```text
functional checkpoint hash
key/plaintext common membership
common scan set and total scan count
variable budget and chain count
fault source hash and loaded count
direct Q/QN exclusion policy
DFT protocol and ATPG option hash
connectivity preflight status
```

Otherwise report `INVALID` and the exact failed invariant.

