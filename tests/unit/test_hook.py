import stat
import sys
from pathlib import Path

from learnloop.cli import HOOK_MARKER, _hook_text, cmd_init


def test_hook_text_contains_marker():
    text = _hook_text()
    assert HOOK_MARKER in text
    assert text.startswith("#!/bin/sh\n")
    assert text.endswith("exit 0\n")


def test_hook_text_handles_spaces_and_backslashes():
    fake_python = r"C:\Program Files\Python 311\python.exe"
    text = _hook_text(fake_python)
    expected_path = "C:/Program Files/Python 311/python.exe"
    assert f'"{expected_path}"' in text
    assert "\\" not in text


def test_cmd_init_in_git_repo(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    rc = cmd_init(tmp_path)
    assert rc == 0

    hook_file = git_dir / "hooks" / "post-commit"
    assert hook_file.is_file()
    content = hook_file.read_text("utf-8")
    assert HOOK_MARKER in content
    assert "learnloop record-commit" in content

    # Check executable permission on POSIX
    if sys.platform != "win32":
        mode = hook_file.stat().st_mode
        assert mode & stat.S_IXUSR

    # Check queue and gitignore
    assert (tmp_path / ".learn" / "queue").is_dir()
    assert (tmp_path / ".learn" / ".gitignore").read_text("utf-8") == "queue/\n"


def test_cmd_init_idempotent(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    assert cmd_init(tmp_path) == 0
    hook_file = git_dir / "hooks" / "post-commit"
    first_content = hook_file.read_text("utf-8")

    # Run init again
    assert cmd_init(tmp_path) == 0
    second_content = hook_file.read_text("utf-8")
    assert first_content == second_content


def test_cmd_init_foreign_hook_refusal(tmp_path: Path):
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    foreign_hook = hooks_dir / "post-commit"
    foreign_content = "#!/bin/sh\necho 'custom hook'\n"
    foreign_hook.write_text(foreign_content, encoding="utf-8")

    rc = cmd_init(tmp_path)
    assert rc == 1
    # Check foreign hook was not overwritten
    assert foreign_hook.read_text("utf-8") == foreign_content


def test_cmd_init_non_git_repo(tmp_path: Path):
    rc = cmd_init(tmp_path)
    assert rc == 1
    assert (tmp_path / ".learn" / "queue").is_dir()


def test_hook_template_constant():
    from learnloop.cli import HOOK_TEMPLATE

    assert HOOK_MARKER in HOOK_TEMPLATE
    assert "{python}" in HOOK_TEMPLATE


def test_hook_single_source_of_truth_and_no_stray_copies():
    repo_root = Path(__file__).parents[2]

    # Reference copy in integrations/hooks/post-commit must exactly match _hook_text("python")
    integrations_hook = repo_root / "integrations" / "hooks" / "post-commit"
    assert integrations_hook.is_file()
    assert integrations_hook.read_text("utf-8") == _hook_text("python")

    # Stray copy in src/learnloop/hooks must not exist
    stray_hook = repo_root / "src" / "learnloop" / "hooks" / "post-commit"
    assert not stray_hook.exists(), "src/learnloop/hooks/post-commit must be deleted"

