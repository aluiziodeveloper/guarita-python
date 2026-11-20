import base64

import pytest

from guarita.dlp import DlpGate, is_valid_cpf, shannon_entropy
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


async def test_detects_cpf_hidden_in_base64() -> None:
    encoded = base64.b64encode(f"cpf={SYNTHETIC_CPF}".encode()).decode()

    decision = await DlpGate().decide(Call("send_message", {"blob": encoded}))

    assert decision.allowed is False
    assert "cpf" in decision.reason
    assert SYNTHETIC_CPF not in decision.reason


async def test_detects_double_encoded_secret() -> None:
    secret = "AKIA" + "0123456789ABCDEF"
    once = base64.b64encode(secret.encode()).decode()
    twice = base64.b64encode(once.encode()).decode()

    decision = await DlpGate().decide(Call("send_message", {"blob": twice}))

    assert decision.allowed is False
    assert "aws-key" in decision.reason


async def test_flags_high_entropy_token_without_flagging_normal_prose() -> None:
    high = "aZ9kL2mQ8xP4vN7wR1yT6bC3dF5gH0jK"
    assert shannon_entropy(high) > 4.5

    blocked = await DlpGate().decide(Call("send_message", {"note": f"chave={high}"}))
    clean = await DlpGate().decide(
        Call("send_message", {"note": "Relatorio_de_vendas_consolidado_trimestre_atual"})
    )

    assert blocked.allowed is False
    assert "high-entropy" in blocked.reason
    assert clean.allowed is True
