import pytest

from minicode.openai_adapter import _openai_chat_completions_url


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://api.openai.com", "https://api.openai.com/v1/chat/completions"),
        ("https://api.openai.com/", "https://api.openai.com/v1/chat/completions"),
        ("https://ldoapi.tech/v1", "https://ldoapi.tech/v1/chat/completions"),
        ("https://ldoapi.tech/v1/", "https://ldoapi.tech/v1/chat/completions"),
        (
            "https://proxy.example.com/v1/chat/completions",
            "https://proxy.example.com/v1/chat/completions",
        ),
    ],
)
def test_openai_chat_completions_url_normalizes_base_url(base_url, expected) -> None:
    assert _openai_chat_completions_url(base_url) == expected


@pytest.mark.parametrize("base_url", ["/v1", "v1", ""])
def test_openai_chat_completions_url_rejects_relative_url(base_url) -> None:
    with pytest.raises(ValueError, match="absolute http\\(s\\) URL"):
        _openai_chat_completions_url(base_url)
