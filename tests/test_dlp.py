import pytest

from guarita.dlp import DlpGate, is_valid_cpf
from guarita.domain import Call

pytestmark = pytest.mark.anyio

SYNTHETIC_CPF = "529.982.247-25"
SYNTHETIC_CPF_PLAIN = "52998224725"


def test_validates_cpf_check_digits() -> None:
    assert is_valid_cpf(SYNTHETIC_CPF_PLAIN) is True
    assert is_valid_cpf("11111111111") is False
    assert is_valid_cpf("12345678900") is False
    assert is_valid_cpf("123") is False


async def test_allows_clean_text_and_invalid_11_digit_ids() -> None:
    gate = DlpGate()
    decision = await gate.decide(
        Call("open_ticket", {"body": "Pedido 12345678900 entregue na quinta."})
    )

    assert decision.allowed is True


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        ({"body": f"Cliente CPF {SYNTHETIC_CPF}"}, "cpf"),
        ({"nested": [{"doc": SYNTHETIC_CPF_PLAIN}]}, "cpf"),
        ({"token": "AKIA" + "0123456789ABCDEF"}, "aws-key"),
        ({"token": "ghp_" + "a1B2c3D4" * 4 + "1234"}, "github-token"),
        ({"key": "-----BEGIN " + "OPENSSH PRIVATE KEY-----"}, "private-key"),
    ],
)
async def test_blocks_secrets_and_cpfs_without_echoing_them(
    payload: dict[str, object], kind: str
) -> None:
    decision = await DlpGate().decide(Call("send_message", payload))

    assert decision.allowed is False
    assert kind in decision.reason
    assert SYNTHETIC_CPF not in decision.reason
    assert SYNTHETIC_CPF_PLAIN not in decision.reason
    assert "0123456789ABCDEF" not in decision.reason
