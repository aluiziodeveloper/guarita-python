"""Contenção de servidores MCP stdio em contêiner Docker sem rede e sem privilégios."""

from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_PREFIXES: tuple[Path, ...] = (
    Path("/etc"),
    Path("/root"),
    Path("/proc"),
    Path("/sys"),
    Path("/var/run/docker.sock"),
    Path("/run/docker.sock"),
)


class SandboxError(ValueError):
    """Configuração insegura para o contêiner do servidor stdio."""


@dataclass(frozen=True)
class Mount:
    host_path: Path
    container_path: str
    read_only: bool = True


@dataclass(frozen=True)
class SandboxConfig:
    image: str
    command: tuple[str, ...]
    mounts: tuple[Mount, ...] = ()
    memory: str = "256m"
    cpus: str = "0.5"
    pids_limit: int = 64
    user: str = "65534:65534"


def _validate_mount(mount: Mount) -> Path:
    resolved = mount.host_path.expanduser().resolve(strict=False)
    for forbidden in FORBIDDEN_PREFIXES:
        if resolved == forbidden or resolved.is_relative_to(forbidden):
            raise SandboxError(f"montagem proibida: {resolved}")
    if ".ssh" in resolved.parts:
        raise SandboxError(f"montagem proibida (chaves SSH): {resolved}")
    return resolved


def build_docker_command(config: SandboxConfig) -> list[str]:
    """Monta `docker run` travado: sem rede, somente leitura, sem capabilities e sem root."""
    if not config.image.strip() or not config.command:
        raise SandboxError("imagem e comando do servidor são obrigatórios")
    argv = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        config.memory,
        "--cpus",
        config.cpus,
        "--pids-limit",
        str(config.pids_limit),
        "--user",
        config.user,
    ]
    for mount in config.mounts:
        real_path = _validate_mount(mount)
        mode = "ro" if mount.read_only else "rw"
        argv.extend(["-v", f"{real_path}:{mount.container_path}:{mode}"])
    argv.append(config.image)
    argv.extend(config.command)
    return argv
