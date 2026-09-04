from __future__ import annotations

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.system_status import (
    LatestBackupStatusSchema,
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

    return f"<code>" f"{_ltr(value)}" f"</code>"


# =========================================================
# STATUS
# =========================================================


def _status_icon(
    enabled: bool,
) -> str:
    """
    Return boolean status indicator.
    """

    return "🟢" if enabled else "🔴"


def _scheduler_icon(
    status: SchedulerRuntimeStatus,
) -> str:
    """
    Return scheduler runtime indicator.
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
    Return Persian scheduler runtime label.
    """

    if status == SchedulerRuntimeStatus.RUNNING:
        return "در حال اجرا"

    if status == SchedulerRuntimeStatus.PAUSED:
        return "در حالت مکث"

    return "متوقف"


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
    Format percentage.
    """

    return f"{value:.1f}%"


def _format_bytes(
    value: int,
) -> str:
    """
    Format bytes using an appropriate unit.
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
    Format application uptime as compact Persian duration.
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
# BACKUP
# =========================================================


def _backup_status(
    backup: LatestBackupStatusSchema,
) -> tuple[str, str]:
    """
    Return latest backup visual status.
    """

    if backup.status == BackupStatus.SUCCESS:
        return (
            "🟢",
            "موفق",
        )

    return (
        "🔴",
        "ناموفق",
    )


def _format_backup_time(
    backup: LatestBackupStatusSchema,
) -> str:
    """
    Format latest backup start timestamp.
    """

    return backup.started_at.strftime("%Y-%m-%d %H:%M")


# =========================================================
# OVERVIEW
# =========================================================


def format_system_status(
    status: SystemStatusSchema,
) -> str:
    """
    Format compact system-status dashboard.
    """

    overall_icon, overall_text = _overall_status(status)

    if status.project_count:
        project_summary = (
            f"{status.enabled_project_count} فعال " f"از {status.project_count} پروژه"
        )
    else:
        project_summary = "پروژه‌ای ثبت نشده است"

    if status.latest_backup is None:
        backup_summary = "هنوز بکاپی ثبت نشده است"

    else:
        backup_icon, backup_text = _backup_status(status.latest_backup)

        backup_summary = (
            f"{backup_icon} " f"{backup_text} — " f"{status.latest_backup.project_name}"
        )

    return (
        "🤖 <b>وضعیت سیستم</b>\n"
        "\n"
        f"{overall_icon} "
        f"{overall_text}\n"
        "\n"
        "\n"
        "⏱ <b>زمان اجرا</b>\n"
        f"{_format_uptime(status.uptime_seconds)}\n"
        "\n"
        "\n"
        "📦 <b>پروژه‌ها</b>\n"
        f"{project_summary}\n"
        "\n"
        "\n"
        "🗃 <b>آخرین بکاپ</b>\n"
        f"{backup_summary}\n"
        "\n"
        "\n"
        "برای مشاهده جزئیات، "
        "یکی از بخش‌های زیر را انتخاب کنید."
    )


# =========================================================
# SERVICES PAGE
# =========================================================


def format_system_services(
    status: SystemStatusSchema,
) -> str:
    """
    Format application services page.
    """

    scheduler_suffix = ""

    if status.scheduler_status == SchedulerRuntimeStatus.PAUSED:
        scheduler_suffix = " — در حالت مکث"

    elif status.scheduler_status == SchedulerRuntimeStatus.STOPPED:
        scheduler_suffix = " — متوقف"

    bot_suffix = "" if status.bot_enabled else " — غیرفعال"

    backup_suffix = "" if status.backup_enabled else " — غیرفعال"

    database_suffix = "" if status.database_healthy else " — در دسترس نیست"

    retention_suffix = "" if status.retention_enabled else " — غیرفعال"

    return (
        "⚙️ <b>وضعیت سرویس‌ها</b>\n"
        "\n"
        f"{_status_icon(status.bot_enabled)} "
        f"ربات{bot_suffix}\n"
        "\n"
        f"{_status_icon(status.backup_enabled)} "
        f"سیستم بکاپ{backup_suffix}\n"
        "\n"
        f"{_scheduler_icon(status.scheduler_status)} "
        f"زمان‌بندی{scheduler_suffix}\n"
        "\n"
        f"{_status_icon(status.database_healthy)} "
        f"دیتابیس{database_suffix}\n"
        "\n"
        f"{_status_icon(status.proxy_enabled)} "
        "پروکسی"
        f"{'' if status.proxy_enabled else ' — غیرفعال'}\n"
        "\n"
        f"{_status_icon(status.retention_enabled)} "
        f"نگهداری بکاپ{retention_suffix}"
    )


# =========================================================
# RESOURCES PAGE
# =========================================================


def format_system_resources(
    status: SystemStatusSchema,
) -> str:
    """
    Format host resource usage page.
    """

    return (
        "📊 <b>منابع سیستم</b>\n"
        "\n"
        "\n"
        "🧩 <b>حافظه</b>\n"
        "\n"
        f"استفاده: "
        f"{_code(_percentage(status.memory_usage_percent))}\n"
        f"مصرف‌شده: "
        f"{_code(_format_bytes(status.memory_used_bytes))}\n"
        f"کل: "
        f"{_code(_format_bytes(status.memory_total_bytes))}\n"
        f"آزاد: "
        f"{_code(_format_bytes(status.memory_available_bytes))}\n"
        "\n"
        "\n"
        "⚙️ <b>پردازنده</b>\n"
        "\n"
        f"استفاده: "
        f"{_code(_percentage(status.cpu_usage_percent))}\n"
        f"هسته فیزیکی: "
        f"{_code(_physical_cores(status.cpu_physical_cores))}\n"
        f"هسته منطقی: "
        f"{_code(str(status.cpu_logical_cores))}\n"
        "\n"
        "\n"
        "💽 <b>فضای ذخیره‌سازی</b>\n"
        "\n"
        f"استفاده: "
        f"{_code(_percentage(status.disk_usage_percent))}\n"
        f"مصرف‌شده: "
        f"{_code(_format_bytes(status.disk_used_bytes))}\n"
        f"کل: "
        f"{_code(_format_bytes(status.disk_total_bytes))}\n"
        f"آزاد: "
        f"{_code(_format_bytes(status.disk_free_bytes))}"
    )


# =========================================================
# BACKUP PAGE
# =========================================================


def format_system_backup(
    status: SystemStatusSchema,
) -> str:
    """
    Format latest backup status page.
    """

    backup = status.latest_backup

    if backup is None:
        return "🗃 <b>آخرین بکاپ</b>\n" "\n" "هنوز هیچ بکاپی ثبت نشده است."

    icon, label = _backup_status(backup)

    text = (
        "🗃 <b>آخرین بکاپ</b>\n"
        "\n"
        f"{icon} <b>{label}</b>\n"
        "\n"
        "پروژه\n"
        f"<b>{backup.project_name}</b>\n"
        "\n"
        "زمان اجرا\n"
        f"{_code(_format_backup_time(backup))}\n"
    )

    if backup.status == BackupStatus.SUCCESS:
        text += "\n" "حجم آرشیو\n" f"{_code(_format_bytes(backup.archive_size_bytes))}"

        return text

    if backup.error_message:
        text += "\n" "\n" "خطا\n" f"<code>{backup.error_message}</code>"

    return text


# =========================================================
# PROJECTS PAGE
# =========================================================


def format_system_projects(
    status: SystemStatusSchema,
) -> str:
    """
    Format project statistics page.
    """

    return (
        "📦 <b>وضعیت پروژه‌ها</b>\n"
        "\n"
        f"کل پروژه‌ها: "
        f"<b>{status.project_count}</b>\n"
        "\n"
        f"پروژه‌های فعال: "
        f"<b>{status.enabled_project_count}</b>\n"
        "\n"
        f"زمان‌بندی فعال: "
        f"<b>{status.scheduled_project_count}</b>\n"
        "\n"
        f"ادمین‌ها: "
        f"<b>{status.admin_count}</b>"
    )


# =========================================================
# SYSTEM PAGE
# =========================================================


def format_system_information(
    status: SystemStatusSchema,
) -> str:
    """
    Format operating-system information page.
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
        f"{_code(status.python_version)}\n"
        "\n"
        "زمان اجرای برنامه\n"
        f"{_format_uptime(status.uptime_seconds)}"
    )


__all__ = [
    "format_system_backup",
    "format_system_information",
    "format_system_projects",
    "format_system_resources",
    "format_system_services",
    "format_system_status",
]
