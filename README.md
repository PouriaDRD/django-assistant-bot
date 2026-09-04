# 🤖 Django Assistant Bot

### Production-oriented Telegram backup and management assistant for Django projects

Manage Django project backups, schedules, retention, administrators, Telegram delivery, proxy connectivity, backup history, and system health from one bot.


[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)


[🚀 Quick Start](#-quick-start)
•
[✨ Features](#-features)
•
[🧰 Installation](#-installation)
•
[⚙️ Configuration](#️-configuration)
•
[🛠 CLI](#-management-cli)
•
[🏗 Architecture](#-architecture)

---

## ✨ Overview

**Django Assistant Bot** is a Telegram-based administration and backup system designed for managing one or more Django projects from a single interface.

It can:

- create SQLite database backups
- include Django media files
- build ZIP archives
- calculate SHA-256 checksums
- schedule automatic backups
- enforce per-project concurrency protection
- maintain backup history
- clean old successful backups using retention policies
- deliver successful backup archives through Telegram
- manage Telegram administrators
- configure and test Telegram proxies
- report system and database health
- expose internal benchmark tools
- run as a managed `systemd` service in production

The project uses a layered architecture that separates persistence, business logic, scheduling, backup execution, delivery, and Telegram transport.

---

# 🚀 Quick Start

> [!IMPORTANT]
> The production installer must be executed as **root**.
>
> Ubuntu and Debian are the currently supported production platforms.

### One-line installation

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/PouriaDRD/django-assistant-bot/main/install.sh)
```

### Or download the manager first

```bash
curl -fsSL \
  https://raw.githubusercontent.com/PouriaDRD/django-assistant-bot/main/install.sh \
  -o /root/django-assistant-bot-installer.sh

chmod +x /root/django-assistant-bot-installer.sh

/root/django-assistant-bot-installer.sh
```

The interactive manager opens with:

```text
╔════════════════════════════════════════════╗
║        Django Assistant Bot Manager       ║
╚════════════════════════════════════════════╝

1) Install
2) Update
3) Service Status
4) Restart Service
5) View Logs
6) Uninstall
7) Exit
```

During installation, the manager asks for the required environment values and creates `.env` automatically.

---

# ✨ Features

## 📦 Django project management

Manage multiple Django projects from Telegram.

Each project can define:

- SQLite database path
- media directory
- media backup status
- backup schedule
- project-specific backup history

Database and media paths are validated before they are stored and again before backup execution.

---

## 💾 Backup pipeline

A backup can contain the Django SQLite database and, optionally, the project media directory.

```text
Django Project
      │
      ├── SQLite Database
      │       │
      │       └── Safe SQLite Backup
      │
      └── Media Directory
              │
              └── Recursive Media Collection
                       │
                       ▼
                   ZIP Archive
                       │
                       ▼
                SHA-256 Checksum
```

The backup engine is independent from Telegram.

---

## 🧱 Collision-resistant archive names

Backup archive names include a timestamp and unique suffix so multiple backups created in the same second do not overwrite each other.

```text
<project_id>_<timestamp>_<unique_suffix>.zip
```

Example:

```text
3a9ab80d585445f5be99beaf427ccb6a_20260904_190626_8dead8a3.zip
```

---

## 🖼 Media backups

Optional media backup support includes:

- nested directory preservation
- many-file workloads
- large media files
- media file counting
- total media size calculation
- safe path validation

The media tree is processed without loading the entire directory into memory at once.

---

## 🗜 Configurable ZIP compression

ZIP compression level can be managed from Telegram.

Supported values:

```text
0 → no compression
1 → fastest compression
...
6 → default
...
9 → maximum compression
```

Default:

```text
6
```

---

## ⏰ Automatic scheduling

Backups can run automatically using APScheduler.

Supported scheduling units:

- minutes
- hours
- days

Scheduler behavior includes:

- one scheduled job per enabled project
- `coalesce=True`
- `max_instances=1` per scheduler job
- missed-run grace handling
- schedule restoration after application startup
- blocking backup work moved outside the asyncio event loop

Production environments enforce safer minimum schedule choices, while development/testing can use shorter intervals.

---

## 🔒 Concurrency protection

The backup coordinator prevents two backups of the **same project** from running simultaneously.

Different projects may still run concurrently.

---

## 🧹 Retention

Retention can automatically remove older successful backups.

Retention is intentionally conservative:

- only successful backup history participates
- failed backup history is preserved
- unlink failure preserves history
- stale history for a missing archive can be reconciled
- retention failures do not convert a successful backup into a failed backup

---

## 📜 Backup history

Backup history is available globally and per project.

Stored information can include:

- project
- status
- archive path
- archive size
- database size
- media size
- media file count
- checksum
- creation time
- failure details

Telegram supports pagination and detailed history views.

---

## 📤 Telegram delivery

Successful backup archives can be delivered to configured administrators.

Delivery failure is isolated from backup success.

---

## 👤 Administrator management

Multiple Telegram administrators are supported.

The application includes protection against accidentally removing the last administrator.

Initial administrators are configured during installation through:

```text
Bootstrap Admin IDs (comma-separated):
```

Example:

```text
123456789,987654321,555555555
```

---

## 🌐 Telegram proxy support

Telegram traffic can optionally use a proxy.

Supported schemes:

```text
http://
socks4://
socks5://
```

Proxy support includes authenticated URLs, IPv4/IPv6, testing, masking, safe enable/disable, and CLI recovery.

---

## 🩺 System status

The Telegram system status screen can report:

- bot status
- backup status
- proxy status
- retention status
- scheduler status
- number of projects
- number of administrators
- OS
- Python version
- architecture
- CPU usage
- memory usage
- disk usage
- uptime
- database health
- latest backup status

---

## 📊 Performance tools

Backup benchmark:

```bash
python main.py benchmark backup <project_id>
```

Compression benchmark:

```bash
python main.py benchmark compression <project_id> --runs 5
```

Benchmark archives are temporary and cleaned up automatically.

---

# 🧰 Installation

## Production requirements

The production installer currently expects:

- Linux
- Ubuntu or Debian
- root access
- `systemd`
- network access
- Git
- Python 3.13

---

## Root installation

The manager must be run as root.

Application path:

```text
/root/django-assistant-bot
```

Service user:

```text
root
```

---

# 📁 Production filesystem layout

```text
/root/django-assistant-bot/
├── .venv/
├── .env -> /etc/django-assistant-bot/.env
├── data -> /var/lib/django-assistant-bot
├── logs -> /var/log/django-assistant-bot
├── alembic/
├── src/
├── main.py
└── ...
```

Persistent configuration:

```text
/etc/django-assistant-bot/.env
```

Persistent data:

```text
/var/lib/django-assistant-bot/
├── bot.sqlite3
└── backups/
```

Logs:

```text
/var/log/django-assistant-bot/
```

---

# ⚙️ Configuration

Installer prompts:

```text
Environment [production]:
Telegram Bot Token:
Bootstrap Admin IDs (comma-separated):
Log Level [INFO]:
Configure Telegram proxy now? [y/N]:
```

Example generated `.env`:

```env
DAB_ENVIRONMENT=production
DAB_TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
DAB_BOOTSTRAP_ADMIN_IDS=[123456789,987654321]
DAB_LOG_LEVEL=INFO
```

`Log Level` is optional and defaults to `INFO`.

---

# 🌐 Optional proxy setup

Proxy setup is optional during installation.

```text
Configure Telegram proxy now? [y/N]:
```

If skipped, Telegram uses a direct connection.

Proxy settings are persisted in SQLite, not in `.env`.

---

# 🖥 Installer Manager

Run:

```bash
cd /root/django-assistant-bot
bash install.sh
```

Menu:

```text
1) Install
2) Update
3) Service Status
4) Restart Service
5) View Logs
6) Uninstall
7) Exit
```

Update preserves persistent state.

Uninstall preserves database, backups, configuration, and logs by default. A full purge requires typing `DELETE`.

---

# ⚡ Manual service management

```bash
systemctl start django-assistant-bot
systemctl stop django-assistant-bot
systemctl restart django-assistant-bot
systemctl status django-assistant-bot
systemctl enable django-assistant-bot
systemctl disable django-assistant-bot
```

---

# 🧑‍💻 Telegram commands

```text
/start
/menu
/help
```

Main menu:

```text
[ 📦 پروژه‌ها ] [ 💾 بکاپ ]
[ ⏰ زمان‌بندی ] [ ⚙️ تنظیمات ]
[ 👤 ادمین‌ها ] [ 🌐 پروکسی ]
[       🤖 وضعیت سیستم       ]
```

---

# 🛠 Management CLI

Run from:

```bash
cd /root/django-assistant-bot
```

Proxy:

```bash
.venv/bin/python main.py proxy status
.venv/bin/python main.py proxy set
.venv/bin/python main.py proxy test
.venv/bin/python main.py proxy enable
.venv/bin/python main.py proxy disable
.venv/bin/python main.py proxy clear
```

Backup benchmark:

```bash
.venv/bin/python main.py benchmark backup <project_id>
```

Compression benchmark:

```bash
.venv/bin/python main.py benchmark compression <project_id> --runs 5
```

---

# 🏗 Architecture

```text
Telegram
   │
   ▼
Handlers / Middlewares
   │
   ▼
Application Services
   │
   ├── ProjectService
   ├── AdminService
   ├── AppSettingsService
   ├── BackupCoordinator
   ├── BackupSchedulerService
   ├── RetentionService
   └── SystemStatusService
   │
   ▼
Repositories
   │
   ▼
SQLAlchemy
   │
   ▼
SQLite
```

Core backup execution:

```text
BackupCoordinator
       │
       ▼
 BackupService
       │
       ├── SQLite backup
       ├── Media collection
       ├── ZIP archive
       └── SHA-256 checksum
```

Telegram delivery remains isolated from backup success.

---

# 📂 Source layout

```text
src/django_assistant_bot/
├── application.py
├── cli.py
├── cli_proxy.py
├── cli_benchmark.py
├── cli_compression_benchmark.py
├── bot/
├── core/
├── database/
├── repositories/
├── schemas/
└── services/
```

---

# 🗄 Database

Internal persistence uses SQLite.

Production path:

```text
/var/lib/django-assistant-bot/bot.sqlite3
```

Migrations:

```bash
cd /root/django-assistant-bot
.venv/bin/alembic upgrade head
```

---

# 🔐 Security notes

- `.env` is stored under `/etc/django-assistant-bot/.env`
- installer applies restrictive permissions
- proxy credentials are masked in user-facing output
- administrator actions require authorization
- project paths are validated
- partial archives are cleaned up when possible
- full uninstall purge requires explicit confirmation

---

# 🧪 Testing

Run:

```bash
pytest -q
```

Current reliability coverage includes:

- backup execution
- scheduler behavior
- retention and recovery
- Telegram handlers
- proxy behavior
- filesystem failures
- SQLite contention
- same-project concurrency
- multi-project concurrency
- scheduler overlap
- Telegram delivery storms
- proxy/network storms
- large-media workloads
- many-file workloads
- endurance/repeated backups
- resource leak checks
- archive filename collision protection
- benchmark archive cleanup

Current local milestone:

```text
614 passed
```

---

# 🧪 Development setup

```bash
git clone https://github.com/PouriaDRD/django-assistant-bot.git
cd django-assistant-bot

python3.13 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m pip install --no-deps -e .

cp .env.example .env

alembic upgrade head

python main.py
```

Tests:

```bash
pytest -q
```

---

# 🧯 Troubleshooting

Service status:

```bash
systemctl status django-assistant-bot
```

Recent logs:

```bash
journalctl -u django-assistant-bot -n 100 --no-pager
```

Disable a broken proxy:

```bash
cd /root/django-assistant-bot
.venv/bin/python main.py proxy disable
systemctl restart django-assistant-bot
```

Migration:

```bash
cd /root/django-assistant-bot
.venv/bin/alembic current
.venv/bin/alembic upgrade head
```

Backup storage usage:

```bash
du -sh /var/lib/django-assistant-bot/backups
df -h
```

---

# 🔄 Updating

```bash
cd /root/django-assistant-bot
bash install.sh
```

Choose:

```text
2) Update
```

---

# 🗑 Uninstalling

```bash
cd /root/django-assistant-bot
bash install.sh
```

Choose:

```text
6) Uninstall
```

Persistent data is preserved by default.

---

# 🗺 Roadmap

Potential future enhancements:

- additional Django database engines
- remote/object-storage backup targets
- encrypted archives
- scheduled integrity verification
- additional notification policies
- richer observability
- container deployment support

---

# 🤝 Contributing

```bash
git checkout -b feature/my-feature

pytest -q

git add .
git commit -m "feat: add my feature"
```

Before submitting changes, ensure the complete test suite passes.

---

# 📄 License

Django Assistant Bot is released under the **MIT License**.

See [LICENSE](LICENSE).

---

### Django Assistant Bot

Reliable Django backup management through Telegram.

[⬆ Back to top](#-django-assistant-bot)
