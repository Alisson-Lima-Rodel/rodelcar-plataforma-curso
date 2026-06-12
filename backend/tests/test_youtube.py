"""Unidades puras de app.core.youtube (id, formatação de duração e contagem)."""
import pytest

from app.core.youtube import _fmt_contagem, _fmt_duracao, youtube_id


@pytest.mark.parametrize(
    "url,esperado",
    [
        ("https://www.youtube.com/watch?v=6bHlZ9zm30c", "6bHlZ9zm30c"),
        ("https://youtu.be/6bHlZ9zm30c", "6bHlZ9zm30c"),
        ("https://www.youtube.com/watch?v=6bHlZ9zm30c&t=42s", "6bHlZ9zm30c"),
        ("https://www.youtube.com/embed/6bHlZ9zm30c", "6bHlZ9zm30c"),
        ("https://www.youtube.com/shorts/6bHlZ9zm30c", "6bHlZ9zm30c"),
        ("6bHlZ9zm30c", "6bHlZ9zm30c"),
        ("https://exemplo.com/video", None),
        ("", None),
        (None, None),
    ],
)
def test_youtube_id(url, esperado):
    assert youtube_id(url) == esperado


@pytest.mark.parametrize(
    "iso,esperado",
    [
        ("PT3M31S", "03:31"),
        ("PT1H2M3S", "1:02:03"),
        ("PT45S", "00:45"),
        ("PT10M", "10:00"),
        ("lixo", None),
        (None, None),
    ],
)
def test_fmt_duracao(iso, esperado):
    assert _fmt_duracao(iso) == esperado


@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("966", "966"),
        (966, "966"),
        ("12345", "12,3 mil"),
        ("1500000", "1,5 mi"),
        (None, None),
        ("", None),
    ],
)
def test_fmt_contagem(valor, esperado):
    assert _fmt_contagem(valor) == esperado
