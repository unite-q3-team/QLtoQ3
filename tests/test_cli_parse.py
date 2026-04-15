import pytest

from qltoq3.cli_parse import extract_steam_id


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("123456789", "123456789"),
        ("https://steamcommunity.com/sharedfiles/filedetails/?id=987654", "987654"),
        ("steamcommunity.com/sharedfiles/filedetails/?id=4567", "4567"),
        ("/sharedfiles/filedetails/?id=42", "42"),
        ("?id=777&searchtext=map", "777"),
    ],
)
def test_extract_steam_id_from_supported_token_formats(token: str, expected: str) -> None:
    assert extract_steam_id(token) == expected


@pytest.mark.parametrize(
    "token",
    [
        "",
        "   ",
        "https://steamcommunity.com/sharedfiles/filedetails/?id=abc",
        "steamcommunity.com/sharedfiles/filedetails/?searchtext=q3",
        "no-id-here",
    ],
)
def test_extract_steam_id_returns_none_for_invalid_tokens(token: str) -> None:
    assert extract_steam_id(token) is None
