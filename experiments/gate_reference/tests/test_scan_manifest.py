from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "dft" / "partial_scan_manifest.txt"


def _rows():
    rows = []
    for line in MANIFEST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        role, selector = line.split("|", 1)
        rows.append((role, selector))
    return rows


def _expanded_count(selector):
    if "[0:" not in selector:
        return 1
    end = int(selector.rsplit("[0:", 1)[1].split("]", 1)[0])
    return end + 1


def test_declared_scan_population():
    rows = _rows()
    counts = {role: sum(_expanded_count(selector) for row_role, selector in rows if row_role == role) for role in {
        "target_mc9", "aes_decoy", "data_control_decoy", "status_control_decoy"
    }}
    assert counts == {"target_mc9": 1, "aes_decoy": 127, "data_control_decoy": 120, "status_control_decoy": 8}
    assert sum(counts.values()) == 256


def test_key_registers_are_excluded():
    text = MANIFEST.read_text()
    assert "key_reg" not in text
    assert "round_key" not in text
