#!/usr/bin/env bash

set -Eeuo pipefail


# =========================================================
# DJANGO ASSISTANT BOT
# Production Installer / Manager
# =========================================================


# ---------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------

APP_NAME="django-assistant-bot"
SERVICE_NAME="django-assistant-bot"

REPOSITORY_URL="https://github.com/PouriaDRD/django-assistant-bot.git"
REPOSITORY_BRANCH="main"


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

INSTALL_DIR="/root/django-assistant-bot"

VENV_DIR="${INSTALL_DIR}/.venv"

CONFIG_DIR="/etc/django-assistant-bot"
ENV_FILE="${CONFIG_DIR}/.env"

DATA_DIR="/var/lib/django-assistant-bot"
BACKUP_DIR="${DATA_DIR}/backups"

LOG_DIR="/var/log/django-assistant-bot"

SYSTEMD_SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"


# ---------------------------------------------------------
# PYTHON
# ---------------------------------------------------------

PYTHON_VERSION="3.13"
PYTHON_BIN="python3.13"


# =========================================================
# COLORS
# =========================================================


if [[ -t 1 ]]; then
    COLOR_RESET="\033[0m"
    COLOR_RED="\033[0;31m"
    COLOR_GREEN="\033[0;32m"
    COLOR_YELLOW="\033[0;33m"
    COLOR_BLUE="\033[0;34m"
    COLOR_CYAN="\033[0;36m"
    COLOR_BOLD="\033[1m"
else
    COLOR_RESET=""
    COLOR_RED=""
    COLOR_GREEN=""
    COLOR_YELLOW=""
    COLOR_BLUE=""
    COLOR_CYAN=""
    COLOR_BOLD=""
fi


# =========================================================
# OUTPUT HELPERS
# =========================================================


info() {
    printf "%b\n" "${COLOR_BLUE}ℹ${COLOR_RESET} $*"
}


success() {
    printf "%b\n" "${COLOR_GREEN}✓${COLOR_RESET} $*"
}


warning() {
    printf "%b\n" "${COLOR_YELLOW}⚠${COLOR_RESET} $*"
}


error() {
    printf "%b\n" "${COLOR_RED}✗${COLOR_RESET} $*" >&2
}


section() {
    echo
    printf "%b\n" "${COLOR_BOLD}${COLOR_CYAN}$*${COLOR_RESET}"
    echo
}


pause() {
    echo
    read -r -p "Press Enter to continue..." _
}


clear_screen() {
    if command -v clear >/dev/null 2>&1; then
        clear
    fi
}


# =========================================================
# ERROR HANDLING
# =========================================================


on_error() {
    local exit_code=$?
    local line_number=$1

    echo
    error "Operation failed at line ${line_number}."
    error "Exit code: ${exit_code}"

    return "${exit_code}"
}


trap 'on_error "$LINENO"' ERR


# =========================================================
# ROOT CHECK
# =========================================================


require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        error "This manager must be run as root."
        echo
        echo "Run:"
        echo
        echo "  sudo bash install.sh"
        echo

        exit 1
    fi
}


# =========================================================
# PLATFORM
# =========================================================


load_os_information() {
    if [[ ! -f /etc/os-release ]]; then
        error "Unable to detect Linux distribution."
        return 1
    fi

    # shellcheck disable=SC1091
    source /etc/os-release

    OS_ID="${ID:-unknown}"
    OS_NAME="${PRETTY_NAME:-${ID:-unknown}}"
}


validate_platform() {
    load_os_information

    case "${OS_ID}" in
        ubuntu|debian)
            ;;
        *)
            error "Unsupported Linux distribution: ${OS_NAME}"
            echo
            echo "Currently supported:"
            echo "  - Ubuntu"
            echo "  - Debian"
            echo

            return 1
            ;;
    esac
}


# =========================================================
# COMMAND HELPERS
# =========================================================


command_exists() {
    command -v "$1" >/dev/null 2>&1
}


application_installed() {
    [[ -d "${INSTALL_DIR}/.git" ]] \
        && [[ -x "${VENV_DIR}/bin/python" ]]
}


service_installed() {
    [[ -f "${SYSTEMD_SERVICE_FILE}" ]]
}


run_app_cli() {
    (
        cd "${INSTALL_DIR}"

        "${VENV_DIR}/bin/python" \
            "${INSTALL_DIR}/main.py" \
            "$@"
    )
}


# =========================================================
# VALIDATION HELPERS
# =========================================================


validate_environment() {
    case "$1" in
        production|development|testing)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


validate_log_level() {
    case "$1" in
        DEBUG|INFO|WARNING|ERROR|CRITICAL)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


validate_bot_token() {
    local value="$1"

    [[ -n "${value}" ]] || return 1

    [[ "${value}" == *:* ]] || return 1

    [[ "${value}" != *[[:space:]]* ]] || return 1

    return 0
}


normalize_admin_ids() {
    local raw="$1"
    local normalized=""
    local item=""
    local compact=""

    # Remove all whitespace.
    compact="$(
        printf "%s" "${raw}" \
            | tr -d '[:space:]'
    )"

    if [[ -z "${compact}" ]]; then
        return 1
    fi

    IFS=',' read -r -a admin_items <<< "${compact}"

    declare -A seen=()

    for item in "${admin_items[@]}"; do

        if [[ ! "${item}" =~ ^[0-9]+$ ]]; then
            return 1
        fi

        if [[ "${item}" -le 0 ]]; then
            return 1
        fi

        if [[ -n "${seen[${item}]:-}" ]]; then
            continue
        fi

        seen["${item}"]=1

        if [[ -n "${normalized}" ]]; then
            normalized+=","
        fi

        normalized+="${item}"
    done

    if [[ -z "${normalized}" ]]; then
        return 1
    fi

    printf "%s" "${normalized}"
}


# =========================================================
# SYSTEM PACKAGES
# =========================================================


install_base_packages() {
    section "Installing system dependencies"

    export DEBIAN_FRONTEND=noninteractive

    apt-get update

    apt-get install -y \
        ca-certificates \
        curl \
        git \
        software-properties-common \
        build-essential

    success "Base system dependencies installed."
}


# =========================================================
# PYTHON 3.13
# =========================================================


install_python() {
    section "Checking Python ${PYTHON_VERSION}"

    if command_exists "${PYTHON_BIN}"; then
        success "$("${PYTHON_BIN}" --version) is already installed."
        return
    fi

    warning "Python ${PYTHON_VERSION} was not found."
    info "Attempting installation..."

    export DEBIAN_FRONTEND=noninteractive

    apt-get update

    if apt-cache show python3.13 >/dev/null 2>&1; then
        apt-get install -y \
            python3.13 \
            python3.13-venv \
            python3.13-dev

    elif [[ "${OS_ID}" == "ubuntu" ]]; then
        info "Python 3.13 is not available in the current Ubuntu repositories."
        info "Adding the Deadsnakes Python repository."

        add-apt-repository -y \
            ppa:deadsnakes/ppa

        apt-get update

        apt-get install -y \
            python3.13 \
            python3.13-venv \
            python3.13-dev

    else
        error "Python 3.13 could not be installed automatically."
        echo
        echo "Install Python 3.13 manually and run this manager again."
        echo

        return 1
    fi

    if ! command_exists "${PYTHON_BIN}"; then
        error "Python 3.13 installation failed."
        return 1
    fi

    success "$("${PYTHON_BIN}" --version) installed."
}


# =========================================================
# PERSISTENT DIRECTORIES
# =========================================================


create_persistent_directories() {
    section "Preparing persistent directories"

    mkdir -p \
        "${CONFIG_DIR}" \
        "${DATA_DIR}" \
        "${BACKUP_DIR}" \
        "${LOG_DIR}"

    chmod 700 "${CONFIG_DIR}"
    chmod 700 "${DATA_DIR}"
    chmod 700 "${BACKUP_DIR}"
    chmod 750 "${LOG_DIR}"

    chown -R root:root \
        "${CONFIG_DIR}" \
        "${DATA_DIR}" \
        "${LOG_DIR}"

    success "Persistent directories are ready."
}


# =========================================================
# REPOSITORY
# =========================================================


clone_repository() {
    section "Installing application source"

    if [[ -e "${INSTALL_DIR}" ]]; then

        if [[ -d "${INSTALL_DIR}/.git" ]]; then
            error "Application is already installed:"
            echo
            echo "  ${INSTALL_DIR}"
            echo
            echo "Use the Update option instead."

            return 1
        fi

        if [[ -n "$(ls -A "${INSTALL_DIR}" 2>/dev/null || true)" ]]; then
            error "Install directory already exists and is not empty:"
            echo
            echo "  ${INSTALL_DIR}"

            return 1
        fi

        rmdir "${INSTALL_DIR}" 2>/dev/null || true
    fi

    git clone \
        --branch "${REPOSITORY_BRANCH}" \
        --single-branch \
        "${REPOSITORY_URL}" \
        "${INSTALL_DIR}"

    success "Repository cloned."
}


# =========================================================
# SYMLINKS
# =========================================================


ensure_symlink() {
    local target="$1"
    local link_path="$2"

    if [[ -L "${link_path}" ]]; then

        local current_target
        current_target="$(
            readlink "${link_path}"
        )"

        if [[ "${current_target}" == "${target}" ]]; then
            return
        fi

        rm -f "${link_path}"

    elif [[ -e "${link_path}" ]]; then
        error "Cannot create symlink because path already exists:"
        echo
        echo "  ${link_path}"

        return 1
    fi

    ln -s \
        "${target}" \
        "${link_path}"
}


create_runtime_symlinks() {
    section "Linking persistent storage"

    ensure_symlink \
        "${ENV_FILE}" \
        "${INSTALL_DIR}/.env"

    ensure_symlink \
        "${DATA_DIR}" \
        "${INSTALL_DIR}/data"

    ensure_symlink \
        "${LOG_DIR}" \
        "${INSTALL_DIR}/logs"

    success "Runtime paths linked."
}


# =========================================================
# VIRTUAL ENVIRONMENT
# =========================================================


create_virtual_environment() {
    section "Creating Python virtual environment"

    "${PYTHON_BIN}" -m venv \
        "${VENV_DIR}"

    "${VENV_DIR}/bin/python" -m pip install \
        --upgrade \
        pip \
        setuptools \
        wheel

    success "Virtual environment created."
}


install_python_dependencies() {
    section "Installing Python dependencies"

    (
        cd "${INSTALL_DIR}"

        "${VENV_DIR}/bin/python" -m pip install \
            -r requirements.txt

        # Install the src-layout package itself without
        # resolving dependencies again.
        "${VENV_DIR}/bin/python" -m pip install \
            --no-deps \
            -e .
    )

    success "Python dependencies installed."
}


# =========================================================
# ENV WIZARD
# =========================================================


prompt_environment() {
    local value=""

    while true; do
        read -r -p \
            "Environment [production]: " \
            value

        value="${value:-production}"

        value="$(
            printf "%s" "${value}" \
                | tr '[:upper:]' '[:lower:]'
        )"

        if validate_environment "${value}"; then
            INSTALL_ENVIRONMENT="${value}"
            return
        fi

        warning "Allowed values: production, development, testing"
    done
}


prompt_bot_token() {
    local value=""

    while true; do
        read -r -s -p \
            "Telegram Bot Token: " \
            value

        echo

        if validate_bot_token "${value}"; then
            INSTALL_BOT_TOKEN="${value}"
            return
        fi

        warning "Invalid Telegram bot token."
        warning "A token must be non-empty and contain ':'."
    done
}


prompt_admin_ids() {
    local value=""
    local normalized=""

    while true; do
        echo
        echo "Enter one or more Telegram user IDs."
        echo
        echo "Use comma-separated values, for example:"
        echo
        echo "  123456789,987654321"
        echo

        read -r -p \
            "Bootstrap Admin IDs (comma-separated): " \
            value

        if normalized="$(
            normalize_admin_ids "${value}"
        )"; then
            INSTALL_ADMIN_IDS="${normalized}"
            return
        fi

        warning "Invalid administrator IDs."
        warning "Use positive numeric IDs separated by commas."
    done
}


prompt_log_level() {
    local value=""

    while true; do
        read -r -p \
            "Log Level [INFO]: " \
            value

        value="${value:-INFO}"

        value="$(
            printf "%s" "${value}" \
                | tr '[:lower:]' '[:upper:]'
        )"

        if validate_log_level "${value}"; then
            INSTALL_LOG_LEVEL="${value}"
            return
        fi

        warning "Allowed values:"
        warning "DEBUG, INFO, WARNING, ERROR, CRITICAL"
    done
}


write_environment_file() {
    section "Application configuration"

    echo "Enter the initial application configuration."
    echo

    prompt_environment
    prompt_bot_token
    prompt_admin_ids
    prompt_log_level

    umask 077

    cat > "${ENV_FILE}" <<EOF
# ==========================================================
# DJANGO ASSISTANT BOT
# Production environment configuration
# ==========================================================

DAB_ENVIRONMENT=${INSTALL_ENVIRONMENT}

DAB_TELEGRAM_BOT_TOKEN=${INSTALL_BOT_TOKEN}

DAB_BOOTSTRAP_ADMIN_IDS=[${INSTALL_ADMIN_IDS}]

DAB_LOG_LEVEL=${INSTALL_LOG_LEVEL}
EOF

    chmod 600 "${ENV_FILE}"
    chown root:root "${ENV_FILE}"

    success "Environment configuration created."
}


# =========================================================
# DATABASE MIGRATIONS
# =========================================================


run_migrations() {
    section "Running database migrations"

    (
        cd "${INSTALL_DIR}"

        "${VENV_DIR}/bin/alembic" \
            upgrade head
    )

    success "Database migrations completed."
}


# =========================================================
# SYSTEMD
# =========================================================


write_systemd_service() {
    section "Installing systemd service"

    cat > "${SYSTEMD_SERVICE_FILE}" <<EOF
[Unit]
Description=Django Assistant Bot
Documentation=https://github.com/PouriaDRD/django-assistant-bot
Wants=network-online.target
After=network-online.target

[Service]
Type=simple

User=root
Group=root

WorkingDirectory=${INSTALL_DIR}

ExecStart=${VENV_DIR}/bin/python ${INSTALL_DIR}/main.py

Environment=PYTHONUNBUFFERED=1

Restart=on-failure
RestartSec=5

KillSignal=SIGINT
TimeoutStopSec=30

LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "${SYSTEMD_SERVICE_FILE}"

    systemctl daemon-reload

    systemctl enable "${SERVICE_NAME}"

    success "Systemd service installed."
}


# =========================================================
# PROXY
# =========================================================


configure_optional_proxy() {
    local answer=""

    section "Telegram Proxy"

    read -r -p \
        "Configure Telegram proxy now? [y/N]: " \
        answer

    case "${answer}" in
        y|Y|yes|YES)
            ;;
        *)
            success "Proxy configuration skipped."
            return 0
            ;;
    esac

    echo
    info "The proxy URL will be requested securely by the application."
    echo
    echo "Supported schemes:"
    echo "  http://"
    echo "  socks4://"
    echo "  socks5://"
    echo

    if ! run_app_cli proxy set; then
        warning "Proxy configuration was not saved."
        return 0
    fi

    echo
    info "Testing configured proxy..."

    if ! run_app_cli proxy test; then
        warning "Proxy test failed."
        warning "Proxy will remain disabled."
        return 0
    fi

    success "Proxy connection test succeeded."

    echo

    read -r -p \
        "Enable this proxy? [Y/n]: " \
        answer

    case "${answer}" in
        n|N|no|NO)
            success "Proxy saved but left disabled."
            return 0
            ;;
    esac

    if run_app_cli proxy enable; then
        success "Telegram proxy enabled."
    else
        warning "Proxy could not be enabled."
        warning "Installation will continue with proxy disabled."

        run_app_cli proxy disable >/dev/null 2>&1 || true
    fi
}


# =========================================================
# SERVICE HELPERS
# =========================================================


start_service() {
    section "Starting service"

    systemctl restart "${SERVICE_NAME}"

    sleep 2

    if systemctl is-active \
        --quiet \
        "${SERVICE_NAME}"; then

        success "Django Assistant Bot is running."
        return 0
    fi

    error "Service failed to start."

    echo
    echo "Recent logs:"
    echo

    journalctl \
        -u "${SERVICE_NAME}" \
        -n 50 \
        --no-pager \
        || true

    return 1
}


# =========================================================
# INSTALL
# =========================================================


install_application() {
    clear_screen

    section "Django Assistant Bot — Install"

    if application_installed; then
        warning "Django Assistant Bot is already installed."
        echo
        echo "Use option 2 (Update)."

        pause
        return
    fi

    validate_platform

    echo "Operating system: ${OS_NAME}"
    echo "Install directory: ${INSTALL_DIR}"
    echo "Runtime user: root"
    echo

    read -r -p \
        "Continue installation? [Y/n]: " \
        answer

    case "${answer}" in
        n|N|no|NO)
            info "Installation cancelled."
            pause
            return
            ;;
    esac

    install_base_packages

    install_python

    create_persistent_directories

    clone_repository

    write_environment_file

    create_runtime_symlinks

    create_virtual_environment

    install_python_dependencies

    run_migrations

    configure_optional_proxy

    write_systemd_service

    start_service

    echo
    success "Installation completed successfully."

    echo
    echo "Application:"
    echo "  ${INSTALL_DIR}"
    echo
    echo "Configuration:"
    echo "  ${ENV_FILE}"
    echo
    echo "Database / backups:"
    echo "  ${DATA_DIR}"
    echo
    echo "Logs:"
    echo "  ${LOG_DIR}"
    echo
    echo "Service:"
    echo "  ${SERVICE_NAME}"
    echo

    pause
}


# =========================================================
# UPDATE
# =========================================================


update_application() {
    clear_screen

    section "Django Assistant Bot — Update"

    if ! application_installed; then
        error "Application is not installed."
        pause
        return
    fi

    local was_active="false"

    if systemctl is-active \
        --quiet \
        "${SERVICE_NAME}"; then

        was_active="true"

        info "Stopping service..."

        systemctl stop \
            "${SERVICE_NAME}"
    fi

    section "Updating source code"

    (
        cd "${INSTALL_DIR}"

        git fetch \
            origin \
            "${REPOSITORY_BRANCH}"

        git checkout \
            "${REPOSITORY_BRANCH}"

        git merge \
            --ff-only \
            "origin/${REPOSITORY_BRANCH}"
    )

    success "Source code updated."

    install_python_dependencies

    run_migrations

    write_systemd_service

    section "Restarting application"

    if [[ "${was_active}" == "true" ]]; then
        systemctl restart \
            "${SERVICE_NAME}"
    else
        systemctl start \
            "${SERVICE_NAME}"
    fi

    sleep 2

    if systemctl is-active \
        --quiet \
        "${SERVICE_NAME}"; then

        success "Update completed successfully."
        success "Service is active."

    else
        error "Update completed, but the service is not active."

        echo
        journalctl \
            -u "${SERVICE_NAME}" \
            -n 50 \
            --no-pager \
            || true
    fi

    pause
}


# =========================================================
# SERVICE STATUS
# =========================================================


show_service_status() {
    clear_screen

    section "Django Assistant Bot — Service Status"

    echo "Application:"
    echo "  ${INSTALL_DIR}"
    echo

    echo "Configuration:"
    echo "  ${ENV_FILE}"
    echo

    echo "Persistent data:"
    echo "  ${DATA_DIR}"
    echo

    echo "Application logs:"
    echo "  ${LOG_DIR}"
    echo

    if ! service_installed; then
        warning "Systemd service is not installed."
        pause
        return
    fi

    local active_status
    local enabled_status

    active_status="$(
        systemctl is-active \
            "${SERVICE_NAME}" \
            2>/dev/null \
            || true
    )"

    enabled_status="$(
        systemctl is-enabled \
            "${SERVICE_NAME}" \
            2>/dev/null \
            || true
    )"

    echo "Service state:"
    echo "  ${active_status}"
    echo

    echo "Start on boot:"
    echo "  ${enabled_status}"
    echo

    systemctl status \
        "${SERVICE_NAME}" \
        --no-pager \
        --full \
        || true

    pause
}


# =========================================================
# RESTART SERVICE
# =========================================================


restart_service() {
    clear_screen

    section "Django Assistant Bot — Restart Service"

    if ! service_installed; then
        error "Service is not installed."
        pause
        return
    fi

    info "Restarting Django Assistant Bot..."

    if systemctl restart \
        "${SERVICE_NAME}"; then

        sleep 2

        if systemctl is-active \
            --quiet \
            "${SERVICE_NAME}"; then

            success "Service restarted successfully."
            success "Service is active."

        else
            error "Service restart command completed, but service is not active."
        fi

    else
        error "Service failed to restart."
    fi

    if ! systemctl is-active \
        --quiet \
        "${SERVICE_NAME}"; then

        echo
        echo "Recent logs:"
        echo

        journalctl \
            -u "${SERVICE_NAME}" \
            -n 50 \
            --no-pager \
            || true
    fi

    pause
}


# =========================================================
# LOGS
# =========================================================


view_logs_menu() {
    while true; do
        clear_screen

        section "Django Assistant Bot — Logs"

        echo "1) Follow live logs"
        echo "2) Last 100 lines"
        echo "3) Last 500 lines"
        echo "4) Logs since current boot"
        echo "5) Application log directory"
        echo "6) Back"
        echo

        read -r -p \
            "Select an option: " \
            choice

        case "${choice}" in
            1)
                clear_screen

                echo "Press Ctrl+C to stop following logs."
                echo

                journalctl \
                    -u "${SERVICE_NAME}" \
                    -f \
                    || true
                ;;

            2)
                clear_screen

                journalctl \
                    -u "${SERVICE_NAME}" \
                    -n 100 \
                    --no-pager \
                    || true

                pause
                ;;

            3)
                clear_screen

                journalctl \
                    -u "${SERVICE_NAME}" \
                    -n 500 \
                    --no-pager \
                    || true

                pause
                ;;

            4)
                clear_screen

                journalctl \
                    -u "${SERVICE_NAME}" \
                    -b \
                    --no-pager \
                    || true

                pause
                ;;

            5)
                clear_screen

                section "Application Log Files"

                if [[ -d "${LOG_DIR}" ]]; then
                    ls -lah "${LOG_DIR}"
                else
                    warning "Application log directory does not exist."
                fi

                pause
                ;;

            6)
                return
                ;;

            *)
                warning "Invalid option."
                sleep 1
                ;;
        esac
    done
}


# =========================================================
# UNINSTALL
# =========================================================


remove_systemd_service() {
    if service_installed; then
        systemctl stop \
            "${SERVICE_NAME}" \
            >/dev/null 2>&1 \
            || true

        systemctl disable \
            "${SERVICE_NAME}" \
            >/dev/null 2>&1 \
            || true

        rm -f \
            "${SYSTEMD_SERVICE_FILE}"

        systemctl daemon-reload

        systemctl reset-failed \
            "${SERVICE_NAME}" \
            >/dev/null 2>&1 \
            || true
    fi
}


uninstall_application() {
    clear_screen

    section "Django Assistant Bot — Uninstall"

    if ! application_installed \
        && ! service_installed; then

        warning "Django Assistant Bot does not appear to be installed."
        pause
        return
    fi

    warning "This will remove the application and systemd service."
    echo

    read -r -p \
        "Continue? [y/N]: " \
        answer

    case "${answer}" in
        y|Y|yes|YES)
            ;;
        *)
            info "Uninstall cancelled."
            pause
            return
            ;;
    esac

    echo

    read -r -p \
        "Keep database, backups, configuration and logs? [Y/n]: " \
        keep_data

    case "${keep_data}" in
        n|N|no|NO)
            purge_data="true"
            ;;
        *)
            purge_data="false"
            ;;
    esac

    if [[ "${purge_data}" == "true" ]]; then
        echo
        warning "FULL PURGE REQUESTED."
        echo
        echo "The following will be permanently deleted:"
        echo
        echo "  ${ENV_FILE}"
        echo "  ${DATA_DIR}/bot.sqlite3"
        echo "  ${BACKUP_DIR}"
        echo "  ${LOG_DIR}"
        echo

        read -r -p \
            "Type DELETE to continue: " \
            confirmation

        if [[ "${confirmation}" != "DELETE" ]]; then
            info "Full uninstall cancelled."
            pause
            return
        fi
    fi

    section "Removing service"

    remove_systemd_service

    success "Systemd service removed."

    section "Removing application"

    rm -rf \
        "${INSTALL_DIR}"

    success "Application source removed."

    if [[ "${purge_data}" == "true" ]]; then
        section "Removing persistent data"

        rm -rf \
            "${CONFIG_DIR}" \
            "${DATA_DIR}" \
            "${LOG_DIR}"

        success "Configuration removed."
        success "Database removed."
        success "Backups removed."
        success "Logs removed."

    else
        echo
        success "Persistent data preserved."

        echo
        echo "Configuration:"
        echo "  ${CONFIG_DIR}"
        echo
        echo "Database / backups:"
        echo "  ${DATA_DIR}"
        echo
        echo "Logs:"
        echo "  ${LOG_DIR}"
    fi

    echo
    success "Uninstall completed."

    pause
}


# =========================================================
# MAIN MENU
# =========================================================


show_main_menu() {
    clear_screen

    printf "%b\n" "${COLOR_CYAN}${COLOR_BOLD}"
    echo "╔════════════════════════════════════════════╗"
    echo "║        Django Assistant Bot Manager       ║"
    echo "╚════════════════════════════════════════════╝"
    printf "%b" "${COLOR_RESET}"

    echo

    if service_installed; then
        if systemctl is-active \
            --quiet \
            "${SERVICE_NAME}"; then

            printf "Service: %b\n" \
                "${COLOR_GREEN}● active${COLOR_RESET}"
        else
            printf "Service: %b\n" \
                "${COLOR_RED}● inactive${COLOR_RESET}"
        fi

        echo
    fi

    echo "1) Install"
    echo "2) Update"
    echo "3) Service Status"
    echo "4) Restart Service"
    echo "5) View Logs"
    echo "6) Uninstall"
    echo "7) Exit"
    echo
}


main() {
    require_root

    while true; do
        show_main_menu

        read -r -p \
            "Select an option: " \
            choice

        case "${choice}" in
            1)
                install_application
                ;;

            2)
                update_application
                ;;

            3)
                show_service_status
                ;;

            4)
                restart_service
                ;;

            5)
                view_logs_menu
                ;;

            6)
                uninstall_application
                ;;

            7)
                clear_screen
                echo "Goodbye."
                exit 0
                ;;

            *)
                warning "Invalid option."
                sleep 1
                ;;
        esac
    done
}


# =========================================================
# ENTRYPOINT
# =========================================================


main "$@"