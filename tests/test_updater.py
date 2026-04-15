import pytest

from qltoq3.updater import is_newer_version, version_tuple


@pytest.mark.parametrize(
    ("raw_version", "expected"),
    [
        ("v1.2.3", (1, 2, 3)),
        ("1.2", (1, 2, 0)),
        ("1.2.3-fix1", (1, 2, 3, 1)),
        ("release-2026-04", (2026, 4, 0)),
        ("", (0, 0, 0)),
        ("abc", (0, 0, 0)),
    ],
)
def test_version_tuple_parses_tags_and_pads(raw_version: str, expected: tuple[int, ...]) -> None:
    assert version_tuple(raw_version) == expected


@pytest.mark.parametrize(
    ("latest", "current", "expected"),
    [
        ("v1.0.1", "1.0.0", True),
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "1.0.1", False),
        ("1.2.3-fix2", "1.2.3-fix1", True),
    ],
)
def test_is_newer_version_compares_numeric_parts(
    latest: str, current: str, expected: bool
) -> None:
    assert is_newer_version(latest, current) is expected
