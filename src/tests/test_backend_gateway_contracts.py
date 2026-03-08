from src.application.backend_gateway import BackendGateway


def test_prepare_structured_command_rejects_unknown_executable() -> None:
    executable, arguments, requires_root, risk = BackendGateway.prepare_structured_command(
        {
            "executable": "python",
            "arguments": ["-c", "print(1)"],
            "requires_root": False,
            "risk_level": "low",
        }
    )

    assert executable is None
    assert arguments == []
    assert requires_root is False
    assert risk == "high"


def test_prepare_structured_command_promotes_hydra_to_high_risk() -> None:
    executable, arguments, requires_root, risk = BackendGateway.prepare_structured_command(
        {
            "executable": "hydra",
            "arguments": ["-l", "admin", "-P", "wordlist.txt", "ssh://10.0.0.5"],
            "requires_root": False,
            "risk_level": "low",
        }
    )

    assert executable == "hydra"
    assert arguments == ["-l", "admin", "-P", "wordlist.txt", "ssh://10.0.0.5"]
    assert requires_root is False
    assert risk == "high"


def test_parse_command_with_risk_detects_privileged_nmap_scan() -> None:
    command, arguments, requires_root, risk = BackendGateway.parse_command_with_risk(
        "nmap -sS -p 22 10.0.0.8"
    )

    assert command == "nmap"
    assert arguments == ["-sS", "-p", "22", "10.0.0.8"]
    assert requires_root is True
    assert risk == "high"


def test_parse_command_with_risk_blocks_shell_injection() -> None:
    command, arguments, requires_root, risk = BackendGateway.parse_command_with_risk(
        "nmap 10.0.0.8; whoami"
    )

    assert command is None
    assert arguments == []
    assert requires_root is False
    assert risk == "high"