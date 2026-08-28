from .models import AppConfig


def create_default_config() -> AppConfig:
    return AppConfig()
