from __future__ import annotations

from django_assistant_bot.bot.formatters.proxy import (
    format_proxy_menu,
    mask_proxy_url,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# MASKING
# =========================================================


def test_proxy_without_credentials_is_not_changed() -> None:
    assert mask_proxy_url("socks5://127.0.0.1:1080") == ("socks5://127.0.0.1:1080")


def test_proxy_password_is_masked() -> None:
    result = mask_proxy_url(("socks5://pouria:" "super-secret@127.0.0.1:1080"))

    assert result == ("socks5://pouria:" "••••••••@127.0.0.1:1080")

    assert "super-secret" not in result


def test_empty_proxy_is_empty() -> None:
    assert mask_proxy_url("") == ""


# =========================================================
# MENU
# =========================================================


def test_proxy_menu_disabled_without_url() -> None:
    settings = AppSettingsSchema()

    text = format_proxy_menu(
        settings,
    )

    assert "🔴 غیرفعال" in text

    assert "تنظیم نشده" in text


def test_proxy_menu_active() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    text = format_proxy_menu(
        settings,
    )

    assert "🟢 فعال" in text

    assert "socks5://127.0.0.1:1080" in text


def test_proxy_menu_never_exposes_password() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://pouria:" "super-secret@127.0.0.1:1080"),
    )

    text = format_proxy_menu(
        settings,
    )

    assert "super-secret" not in text

    assert "••••••••" in text
