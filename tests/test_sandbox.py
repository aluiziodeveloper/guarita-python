from pathlib import Path

import pytest

from guarita.sandbox import Mount, SandboxConfig, SandboxError, build_docker_command


def test_builds_locked_down_docker_run_command(tmp_path: Path) -> None:
    data_dir = tmp_path / "notes"
    data_dir.mkdir()
    config = SandboxConfig(
        image="guarita-lab:latest",
        command=("guarita-lab-server", "--variant", "honest"),
        mounts=(Mount(host_path=data_dir, container_path="/data"),),
    )

    argv = build_docker_command(config)

    assert argv[:4] == ["docker", "run", "--rm", "-i"]
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert "--cap-drop" in argv and argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in argv and "no-new-privileges" in argv
    assert "--user" in argv and argv[argv.index("--user") + 1] == "65534:65534"
    assert f"{data_dir.resolve()}:/data:ro" in argv
    assert argv[-4:] == ["guarita-lab:latest", "guarita-lab-server", "--variant", "honest"]


@pytest.mark.parametrize("forbidden", [Path("/var/run/docker.sock"), Path("/etc"), Path("/root")])
def test_refuses_sensitive_host_mounts(forbidden: Path) -> None:
    config = SandboxConfig(
        image="guarita-lab:latest",
        command=("guarita-lab-server",),
        mounts=(Mount(host_path=forbidden, container_path="/mnt"),),
    )

    with pytest.raises(SandboxError, match="montagem proibida"):
        build_docker_command(config)


def test_refuses_symlink_escaping_to_sensitive_host_path(tmp_path: Path) -> None:
    sneaky = tmp_path / "notes-link"
    sneaky.symlink_to("/etc")
    config = SandboxConfig(
        image="guarita-lab:latest",
        command=("guarita-lab-server",),
        mounts=(Mount(host_path=sneaky, container_path="/data"),),
    )

    with pytest.raises(SandboxError, match="montagem proibida"):
        build_docker_command(config)
