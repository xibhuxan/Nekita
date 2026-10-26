import logging

from nekita.logging_setup import MASK, MaskingFormatter, mask

TOKEN = "123456789:AAH" + "x" * 32


def test_mask_oculta_token() -> None:
    assert TOKEN not in mask(f"url https://api.telegram.org/bot{TOKEN}/getMe")
    assert MASK in mask(TOKEN)


def test_mask_no_toca_texto_normal() -> None:
    assert mask("hora 12:30:45 id 123456") == "hora 12:30:45 id 123456"


def test_formatter_enmascara_mensaje_y_traceback() -> None:
    fmt = MaskingFormatter("%(message)s")
    try:
        raise RuntimeError(f"fallo con {TOKEN}")
    except RuntimeError:
        import sys

        rec = logging.LogRecord(
            "t", logging.ERROR, __file__, 1, "token %s", (TOKEN,), sys.exc_info()
        )
    out = fmt.format(rec)
    assert TOKEN not in out
    assert MASK in out
