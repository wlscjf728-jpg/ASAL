# Python Defense Capability Matrix

This directory evaluates representative protection capabilities on the frozen
Python MC-channel oracle. It is separate from `extra_exp/defense_boundary`,
which contains the EDA/netlist validation.

Run the matrix from the repository root with:

```bash
python -m extra_exp.defense_python_matrix.run_defense_matrix \
  --config extra_exp/defense_python_matrix/configs/defense_matrix.json \
  --workers 8 \
  --output extra_exp/defense_python_matrix/results/defense_matrix_summary.json
```

Build the report with:

```bash
python extra_exp/defense_python_matrix/scripts/build_defense_matrix_report.py \
  --input extra_exp/defense_python_matrix/results/defense_matrix_summary.json \
  --output extra_exp/defense_python_matrix/DEFENSE_CAPABILITY_MATRIX_REPORT.md
```

The runner preserves the established rule that only a final second solve of
`UNSAT` proves full-key uniqueness. It records policy blocks and attribution
failures separately from solver ambiguity and unresolved outcomes.

