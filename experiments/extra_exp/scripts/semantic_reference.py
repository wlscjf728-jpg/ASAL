"""Small, dependency-free AES-128 reference used by the MC9 experiment."""
from __future__ import annotations


def gf_mul(a: int, b: int) -> int:
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        a = ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF
        b >>= 1
    return result


def rotl8(value: int, amount: int) -> int:
    return ((value << amount) | (value >> (8 - amount))) & 0xFF


def sbox(value: int) -> int:
    inverse = 0 if value == 0 else next(
        candidate for candidate in range(1, 256) if gf_mul(value, candidate) == 1
    )
    return inverse ^ rotl8(inverse, 1) ^ rotl8(inverse, 2) ^ rotl8(inverse, 3) ^ rotl8(inverse, 4) ^ 0x63


def expand_key(key: bytes) -> list[bytes]:
    if len(key) != 16:
        raise ValueError("AES-128 key must be 16 bytes")
    keys = [bytes(key)]
    rcon = 1
    for _ in range(10):
        old = keys[-1]
        t = bytes((sbox(old[13]), sbox(old[14]), sbox(old[15]), sbox(old[12] ^ 0)))
        t = bytes((t[0] ^ rcon, t[1], t[2], t[3]))
        new = bytearray(16)
        for i in range(4):
            new[i] = old[i] ^ t[i]
        for i in range(4, 16):
            new[i] = old[i] ^ new[i - 4]
        keys.append(bytes(new))
        rcon = ((rcon << 1) ^ 0x1B) & 0xFF if rcon & 0x80 else (rcon << 1)
    return keys


def sub_bytes(state: bytes) -> bytes:
    return bytes(sbox(value) for value in state)


def shift_rows(state: bytes) -> bytes:
    output = bytearray(16)
    for row in range(4):
        for column in range(4):
            output[4 * column + row] = state[4 * ((column + row) % 4) + row]
    return bytes(output)


def mix_columns(state: bytes) -> bytes:
    output = bytearray(16)
    for column in range(4):
        a0, a1, a2, a3 = state[4 * column:4 * column + 4]
        output[4 * column:4 * column + 4] = bytes((
            gf_mul(a0, 2) ^ gf_mul(a1, 3) ^ a2 ^ a3,
            a0 ^ gf_mul(a1, 2) ^ gf_mul(a2, 3) ^ a3,
            a0 ^ a1 ^ gf_mul(a2, 2) ^ gf_mul(a3, 3),
            gf_mul(a0, 3) ^ a1 ^ a2 ^ gf_mul(a3, 2),
        ))
    return bytes(output)


def aes128_round_states(plaintext: bytes, key: bytes) -> tuple[list[bytes], bytes]:
    if len(plaintext) != 16:
        raise ValueError("AES-128 plaintext must be 16 bytes")
    round_keys = expand_key(key)
    state = bytes(a ^ b for a, b in zip(plaintext, round_keys[0]))
    mc_states: list[bytes] = []
    for round_number in range(1, 10):
        state = shift_rows(sub_bytes(state))
        state = mix_columns(state)
        mc_states.append(state)
        state = bytes(a ^ b for a, b in zip(state, round_keys[round_number]))
    state = shift_rows(sub_bytes(state))
    ciphertext = bytes(a ^ b for a, b in zip(state, round_keys[10]))
    return mc_states, ciphertext


def aes128_encrypt(plaintext: bytes, key: bytes) -> bytes:
    return aes128_round_states(plaintext, key)[1]


def mc_state_at_round(plaintext: bytes, key: bytes, round_number: int) -> bytes:
    if not 1 <= round_number <= 9:
        raise ValueError("MC state exists for rounds 1 through 9")
    return aes128_round_states(plaintext, key)[0][round_number - 1]


def mc_bit(plaintext: bytes, key: bytes, round_number: int, bit_index: int) -> int:
    if not 0 <= bit_index < 128:
        raise ValueError("bit index must be in [0, 127]")
    state = mc_state_at_round(plaintext, key, round_number)
    byte_index, bit = divmod(bit_index, 8)
    return (state[byte_index] >> bit) & 1
