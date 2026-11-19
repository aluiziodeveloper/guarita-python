import pytest

from guarita.cli import main


def test_version_prints_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == "guarita 0.1.0\n"


def test_without_arguments_exits_with_zero() -> None:
    assert main([]) == 0
