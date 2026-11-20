"""Autenticação de agentes por JWT (HS256 estrito, sem alg=none) e guarda de Origin."""

from collections.abc import Iterable
from dataclasses import dataclass

import jwt


class AuthError(ValueError):
    """Credencial ausente, expirada, inválida ou fora do escopo."""


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str


class JwtVerifier:
    """Valida JWTs de agentes exigindo algoritmo explícito, sub, exp, aud e iss."""

    def __init__(self, key: str, audience: str, issuer: str) -> None:
        if len(key) < 32:
            raise ValueError("chave HMAC precisa ter pelo menos 32 bytes")
        self._key = key
        self._audience = audience
        self._issuer = issuer

    def verify(self, raw_jwt: str) -> AgentIdentity:
        try:
            claims = jwt.decode(
                raw_jwt,
                self._key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["sub", "exp", "aud", "iss"]},
            )
        except jwt.PyJWTError as error:
            raise AuthError(f"JWT inválido: {error}") from error
        sub = str(claims.get("sub", "")).strip()
        if not sub:
            raise AuthError("JWT sem claim 'sub'")
        return AgentIdentity(agent_id=sub)


class OriginGuard:
    """Recusa cabeçalhos Origin fora da lista permitida (defesa contra DNS rebinding)."""

    def __init__(self, allowed_origins: Iterable[str]) -> None:
        self._allowed = frozenset(o.rstrip("/").lower() for o in allowed_origins)

    def allows(self, origin: str | None) -> bool:
        if origin is None:
            return True
        return origin.rstrip("/").lower() in self._allowed
