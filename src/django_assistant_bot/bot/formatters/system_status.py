from __future__ import annotations

from django_assistant_bot.schemas.system_status import (
    SchedulerRuntimeStatus,
    SystemStatusSchema,
)

# =========================================================
# BIDI
# =========================================================


LTR_ISOLATE = "\u2066"

POP_DIRECTIONAL_ISOLATE = "\u2069"


def _ltr(
    value: str,
) -> str:
    """
    Isolate left-to-right content inside Persian text.
    """

    return f"{LTR_ISOLATE}" f"{value}" f"{POP_DIRECTIONAL_ISOLATE}"


def _code(
    value: str,
) -> str:
    """
    Format isolated left-to-right code value.
    """

    return f"<code>{_ltr(value)}</code>"


# =========================================================
# STATUS
# =========================================================


def _status_icon(
    enabled: bool,
) -> str:
    """
    Return status indicator icon.
    """

    return "🟢" if enabled else "🔴"


def _scheduler_icon(
    status: SchedulerRuntimeStatus,
) -> str:
    """
    Return scheduler status indicator.
    """

    if status == SchedulerRuntimeStatus.RUNNING:
        return "🟢"

    if status == SchedulerRuntimeStatus.PAUSED:
        return "🟡"

    return "🔴"


def _scheduler_text(
    status: SchedulerRuntimeStatus,
) -> str:
    """
    Return Persian scheduler status label.
    """

    if status == SchedulerRuntimeStatus.RUNNING:
        return "در حال اجرا"

    if status == SchedulerRuntimeStatus.PAUSED:
        return "در حالت مکث"

    return "متوقف"


def _database_text(
    healthy: bool,
) -> str:
    """
    Return Persian database health label.
    """

    return "در دسترس" if healthy else "در دسترس نیست"


def _overall_status(
    status: SystemStatusSchema,
) -> tuple[str, str]:
    """
    Resolve overall application status.
    """

    if not status.bot_enabled:
        return (
            "🔴",
            "ربات غیرفعال است",
        )

    if not status.database_healthy:
        return (
            "🔴",
            "دیتابیس در دسترس نیست",
        )

    if status.scheduler_status == SchedulerRuntimeStatus.STOPPED:
        return (
            "🟡",
            "بخشی از سرویس‌ها متوقف هستند",
        )

    if not status.backup_enabled:
        return (
            "🟡",
            "سیستم بکاپ غیرفعال است",
        )

    return (
        "🟢",
        "سیستم در وضعیت عادی قرار دارد",
    )


# =========================================================
# VALUES
# =========================================================


def _percentage(
    value: float,
) -> str:
    """
    Format percentage value.
    """

    return f"{value:.1f}%"


def _format_bytes(
    value: int,
) -> str:
    """
    Format bytes using the most appropriate unit.
    """

    if value <= 0:
        return "0 B"

    size = float(value)

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
        "PB",
    )

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"

            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} PB"


def _physical_cores(
    value: int | None,
) -> str:
    """
    Format physical CPU core count.
    """

    if value is None:
        return "نامشخص"

    return str(value)


def _format_uptime(
    seconds: float,
) -> str:
    """
    Format uptime as a compact Persian duration.
    """

    total_seconds = max(
        0,
        int(seconds),
    )

    days, remainder = divmod(
        total_seconds,
        86_400,
    )

    hours, remainder = divmod(
        remainder,
        3_600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    parts: list[str] = []

    if days:
        parts.append(f"{days} روز")

    if hours:
        parts.append(f"{hours} ساعت")

    if minutes:
        parts.append(f"{minutes} دقیقه")

    if not parts:
        parts.append(f"{seconds} ثانیه")

    return " و ".join(parts[:2])


# =========================================================
# OPERATING SYSTEM
# =========================================================


def _os_name(
    status: SystemStatusSchema,
) -> str:
    """
    Return compact operating-system name.
    """

    version = status.operating_system_version

    release = (
        version.split(
            " ",
            maxsplit=1,
        )[0]
        if version
        else ""
    )

    if release.isdigit():
        return f"{status.operating_system} " f"{release}"

    return status.operating_system


def _os_version(
    status: SystemStatusSchema,
) -> str:
    """
    Extract operating-system build/version.
    """

    version = status.operating_system_version

    if "(" in version and ")" in version:
        return version.split(
            "(",
            maxsplit=1,
        )[1].rsplit(
            ")",
            maxsplit=1,
        )[0]

    return version or "Unknown"


# =========================================================
# SECTIONS
# =========================================================


def _format_services(
    status: SystemStatusSchema,
) -> str:
    """
    Format application services section.
    """

    scheduler_suffix = ""

    if status.scheduler_status == SchedulerRuntimeStatus.PAUSED:
        scheduler_suffix = " — در حالت مکث"

    elif status.scheduler_status == SchedulerRuntimeStatus.STOPPED:
        scheduler_suffix = " — متوقف"

    database_suffix = "" if status.database_healthy else " — در دسترس نیست"

    bot_suffix = "" if status.bot_enabled else " — غیرفعال"

    backup_suffix = "" if status.backup_enabled else " — غیرفعال"

    retention_suffix = "" if status.retention_enabled else " — غیرفعال"

    return (
        "⚙️ <b>سرویس‌ها</b>\n"
        "\n"
        f"{_status_icon(status.bot_enabled)} "
        f"ربات{bot_suffix}\n"
        f"{_status_icon(status.backup_enabled)} "
        f"سیستم بکاپ{backup_suffix}\n"
        f"{_scheduler_icon(status.scheduler_status)} "
        f"زمان‌بندی{scheduler_suffix}\n"
        f"{_status_icon(status.database_healthy)} "
        f"دیتابیس{database_suffix}\n"
        f"{_status_icon(status.proxy_enabled)} "
        "پروکسی\n"
        f"{_status_icon(status.retention_enabled)} "
        f"نگهداری بکاپ{retention_suffix}"
    )


def _format_runtime(
    status: SystemStatusSchema,
) -> str:
    """
    Format application runtime information.
    """

    return "⏱ <b>زمان اجرا</b>\n" "\n" f"{_format_uptime(status.uptime_seconds)}"


def _format_memory(
    status: SystemStatusSchema,
) -> str:
    """
    Format system memory information.
    """

    return (
        "🧩 <b>حافظه</b>\n"
        "\n"
        f"استفاده: {_code(_percentage(status.memory_usage_percent))}\n"
        f"مصرف‌شده: {_code(_format_bytes(status.memory_used_bytes))}\n"
        f"کل: {_code(_format_bytes(status.memory_total_bytes))}\n"
        f"آزاد: {_code(_format_bytes(status.memory_available_bytes))}"
    )


def _format_cpu(
    status: SystemStatusSchema,
) -> str:
    """
    Format processor information.
    """

    return (
        "⚙️ <b>پردازنده</b>\n"
        "\n"
        f"استفاده: {_code(_percentage(status.cpu_usage_percent))}\n"
        f"هسته فیزیکی: {_code(_physical_cores(status.cpu_physical_cores))}\n"
        f"هسته منطقی: {_code(str(status.cpu_logical_cores))}"
    )


def _format_disk(
    status: SystemStatusSchema,
) -> str:
    """
    Format disk usage information.
    """

    return (
        "💽 <b>فضای ذخیره‌سازی</b>\n"
        "\n"
        f"استفاده: {_code(_percentage(status.disk_usage_percent))}\n"
        f"مصرف‌شده: {_code(_format_bytes(status.disk_used_bytes))}\n"
        f"کل: {_code(_format_bytes(status.disk_total_bytes))}\n"
        f"آزاد: {_code(_format_bytes(status.disk_free_bytes))}"
    )


def _format_projects(
    status: SystemStatusSchema,
) -> str:
    """
    Format project statistics.
    """

    return (
        "📦 <b>پروژه‌ها</b>\n"
        "\n"
        f"کل: <b>{status.project_count}</b>\n"
        f"فعال: <b>{status.enabled_project_count}</b>\n"
        f"زمان‌بندی فعال: <b>{status.scheduled_project_count}</b>\n"
        f"ادمین‌ها: <b>{status.admin_count}</b>"
    )


def _format_system(
    status: SystemStatusSchema,
) -> str:
    """
    Format operating-system runtime information.
    """

    return (
        "🖥 <b>اطلاعات سیستم</b>\n"
        "\n"
        "سیستم‌عامل\n"
        f"{_code(_os_name(status))}\n"
        "\n"
        "نسخه\n"
        f"{_code(_os_version(status))}\n"
        "\n"
        "معماری\n"
        f"{_code(status.architecture)}\n"
        "\n"
        "نسخه Python\n"
        f"{_code(status.python_version)}"
    )


# =========================================================
# MAIN
# =========================================================


def format_system_status(
    status: SystemStatusSchema,
) -> str:
    """
    Format application status as a clean Telegram dashboard.
    """

    overall_icon, overall_text = _overall_status(status)

    return (
        "🤖 <b>وضعیت سیستم</b>\n"
        "\n"
        f"{overall_icon} {overall_text}\n"
        "\n"
        "\n"
        f"{_format_services(status)}\n"
        "\n"
        "\n"
        f"{_format_runtime(status)}\n"
        "\n"
        "\n"
        "📊 <b>منابع سیستم</b>\n"
        "\n"
        f"{_format_memory(status)}\n"
        "\n"
        f"{_format_cpu(status)}\n"
        "\n"
        f"{_format_disk(status)}\n"
        "\n"
        "\n"
        f"{_format_projects(status)}\n"
        "\n"
        "\n"
        f"{_format_system(status)}"
    )


__all__ = [
    "format_system_status",
]
