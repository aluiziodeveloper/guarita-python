import asyncio
import base64

from hypothesis import given, settings
from hypothesis import strategies as st

from guarita.dlp import DlpGate, is_valid_cpf, scan_text
from guarita.domain import Call


def make_valid_cpf(base_digits: list[int]) -> str:
    first = (sum(d * w for d, w in zip(base_digits, range(10, 1, -1), strict=True)) * 10) % 11
    dv1 = 0 if first == 10 else first
    with_dv1 = [*base_digits, dv1]
    second = (sum(d * w for d, w in zip(with_dv1, range(11, 1, -1), strict=True)) * 10) % 11
    dv2 = 0 if second == 10 else second
    return "".join(str(d) for d in [*with_dv1, dv2])


valid_cpf_base = st.lists(st.integers(min_value=0, max_value=9), min_size=9, max_size=9).filter(
    lambda ds: len(set(ds)) > 1
)

safe_wrapper = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu"), whitelist_characters=" -"),
    max_size=12,
)


@settings(max_examples=80, deadline=None)
@given(base=valid_cpf_base, punctuated=st.booleans(), prefix=safe_wrapper, suffix=safe_wrapper)
def test_every_generated_valid_cpf_is_blocked_without_leaking(
    base: list[int], punctuated: bool, prefix: str, suffix: str
) -> None:
    cpf = make_valid_cpf(base)
    formatted = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if punctuated else cpf
    text = f"{prefix} {formatted} {suffix}"

    decision = asyncio.run(DlpGate().decide(Call("send_message", {"body": text})))

    assert decision.allowed is False
    assert "cpf" in decision.reason
    assert cpf not in decision.reason
    assert formatted not in decision.reason


@settings(max_examples=80, deadline=None)
@given(base=valid_cpf_base)
def test_every_base64_encoded_valid_cpf_is_detected(base: list[int]) -> None:
    cpf = make_valid_cpf(base)
    encoded = base64.b64encode(cpf.encode()).decode()

    assert "cpf" in scan_text(encoded)


@given(digit=st.integers(min_value=0, max_value=9))
def test_repeated_eleven_digits_are_never_valid_cpfs(digit: int) -> None:
    assert is_valid_cpf(str(digit) * 11) is False
