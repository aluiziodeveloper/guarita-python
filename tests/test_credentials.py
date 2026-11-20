import httpx
import pytest

from guarita.credentials import CredentialError, CredentialVault, UpstreamHttpClient

pytestmark = pytest.mark.anyio


async def test_uses_dedicated_server_credential_and_never_forwards_user_jwt() -> None:
    seen_headers: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append((str(request.url), request.headers.get("authorization")))
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "ok"}], "isError": False}
        )

    vault = CredentialVault({"files": "srv-files-only-cred", "mail": "srv-mail-only-cred"})
    incoming_user_jwt = "eyJhbGciOiJIUzI1NiJ9.user-secret-claims.sig"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        files_client = UpstreamHttpClient("https://files.internal", "files", vault, http)
        mail_client = UpstreamHttpClient("https://mail.internal", "mail", vault, http)
        await files_client.call_tool("read_file", {"path": "notes.txt"})
        await mail_client.call_tool("send_email", {"to": "dev@corp.test"})

    assert seen_headers == [
        ("https://files.internal/mcp", "Bearer srv-files-only-cred"),
        ("https://mail.internal/mcp", "Bearer srv-mail-only-cred"),
    ]
    assert all(incoming_user_jwt not in (hdr or "") for _, hdr in seen_headers)


def test_unknown_upstream_fails_closed() -> None:
    vault = CredentialVault({"files": "srv-files-only-cred"})

    with pytest.raises(CredentialError, match="sem credencial"):
        vault.for_server("billing")
