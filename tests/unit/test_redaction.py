from learnloop.capture.redaction import is_ignored, redact


def test_redacts_common_secrets():
    text = "key=AKIAABCDEFGHIJKLMNOP token: ghp_" + "a" * 36 + " password = hunter2"
    out = redact(text)
    assert "AKIA" not in out and "ghp_" not in out and "hunter2" not in out


def test_redacts_private_key_block():
    pem = "-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----"
    assert redact(f"x {pem} y") == "x [REDACTED] y"


def test_ignores_sensitive_and_noisy_files():
    for p in (".env", "config/.env.local", "certs/server.pem", "uv.lock", "logo.png", ".learn/journal.md"):
        assert is_ignored(p), p
    assert not is_ignored("src/app.py")
