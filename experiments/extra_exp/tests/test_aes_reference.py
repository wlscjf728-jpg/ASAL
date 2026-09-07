import sys
from pathlib import Path

EXTRA_EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTRA_EXP / "scripts"))
from semantic_reference import aes128_encrypt, mc_bit  # noqa: E402


def test_fips_197_aes128_kat():
    assert aes128_encrypt(
        bytes.fromhex("00112233445566778899aabbccddeeff"),
        bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
    ).hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"


def test_mc9_is_one_bit_and_round_bounded():
    key = bytes.fromhex("a66f651322597191ab9f8f8af4c2db61")
    plaintext = bytes(16)
    assert mc_bit(plaintext, key, 1, 9) in (0, 1)
    assert mc_bit(plaintext, key, 2, 9) in (0, 1)
