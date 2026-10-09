import pytest

from learnloop.domain.errors import ValidationError
from learnloop.domain.path_utils import normalise_path, validate_path


def test_normalise_path_forward_slashes():
    assert normalise_path("src/app/main.py") == "src/app/main.py"


def test_normalise_path_windows_backslashes():
    assert normalise_path(r"src\app\x.py") == "src/app/x.py"
    assert normalise_path(r"tests\unit\test_x.py") == "tests/unit/test_x.py"


def test_normalise_path_leading_dot_slash():
    assert normalise_path("./src/x.py") == "src/x.py"
    assert normalise_path(r".\src\x.py") == "src/x.py"
    assert normalise_path("././src/x.py") == "src/x.py"


def test_normalise_path_rejects_absolute_unix():
    with pytest.raises(ValidationError, match="Absolute path not allowed"):
        normalise_path("/src/app/main.py")


def test_normalise_path_rejects_absolute_windows_drive():
    with pytest.raises(ValidationError, match="Absolute path with drive letter not allowed"):
        normalise_path(r"C:\Users\test\project\src\app.py")
    with pytest.raises(ValidationError, match="Absolute path with drive letter not allowed"):
        normalise_path("D:/project/src/app.py")


def test_normalise_path_rejects_parent_traversal():
    with pytest.raises(ValidationError, match="Parent directory traversal"):
        normalise_path("..")
    with pytest.raises(ValidationError, match="Parent directory traversal"):
        normalise_path("../secret.txt")
    with pytest.raises(ValidationError, match="Parent directory traversal"):
        normalise_path("src/../../secret.txt")


def test_normalise_path_rejects_empty():
    with pytest.raises(ValidationError, match="Path cannot be empty"):
        normalise_path("")
    with pytest.raises(ValidationError, match="Path cannot be empty"):
        normalise_path("   ")


def test_normalise_path_rejects_too_long():
    long_path = "a/" * 160 + "file.py"
    with pytest.raises(ValidationError, match="Path exceeds 300 characters"):
        normalise_path(long_path)


def test_validate_path_matches_normalise():
    assert validate_path(r"src\test.py") == "src/test.py"
