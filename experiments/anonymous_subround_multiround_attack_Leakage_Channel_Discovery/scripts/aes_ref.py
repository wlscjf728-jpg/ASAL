"""Re-export the existing Attack 7 AES reference implementation."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / "anonymous_subround_multiround_attack_7_oracle" / "scripts" / "aes_ref.py"
_spec = importlib.util.spec_from_file_location("attack7_aes_ref", _path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load AES reference at {_path}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

SBOX = _module.SBOX
RCON = _module.RCON
xtime = _module.xtime
ark_concrete = _module.ark_concrete
sb_concrete = _module.sb_concrete
sr_concrete = _module.sr_concrete
mc_concrete = _module.mc_concrete
expand_key = _module.expand_key
encrypt_with_trace = _module.encrypt_with_trace
observe_state = _module.observe_state
