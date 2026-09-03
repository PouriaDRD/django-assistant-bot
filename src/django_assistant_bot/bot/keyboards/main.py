from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 پروژه‌ها",
                    callback_data="projects",
                ),
                InlineKeyboardButton(
                    text="💾 بکاپ",
                    callback_data="backup",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏰ زمان‌بندی",
                    callback_data="scheduler",
                ),
                InlineKeyboardButton(
                    text="⚙️ تنظیمات",
                    callback_data="settings",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👤 ادمین‌ها",
                    callback_data="admins",
                ),
                InlineKeyboardButton(
                    text="🌐 پروکسی",
                    callback_data="proxy",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🤖 وضعیت سیستم",
                    callback_data="system_status",
                ),
            ],
        ],
    )
