"""
Конфигурация защиты от brute force для REST API
"""

# ============================================
# BRUTE FORCE PROTECTION CONFIGURATION
# ============================================

BRUTE_FORCE_CONFIG = {
    # ===== БАЗОВЫЕ НАСТРОЙКИ =====
    # Endpoints для защиты (можно добавлять свои)
    "protected_endpoints": [
        "/api/v1/users/access-token/",
    ],
    # Основной лимит попыток
    "max_attempts": 5,  # Максимум попыток
    "lockout_duration": 900,  # 15 минут блокировки
    "attempt_window": 10,  # 300,  # Окно 5 минут для подсчета
    # ===== РАСШИРЕННЫЕ ВРЕМЕННЫЕ ОКНА ===== Защита от медленных атак
    "time_windows": {
        "1h": {
            "duration": 3600,  # 1 час
            "max_attempts": 10,  # Максимум 10 попыток за час
        },
        "24h": {
            "duration": 86400,  # 24 часа
            "max_attempts": 30,  # Максимум 30 попыток за день
        },
        "7d": {
            "duration": 604800,  # 7 дней
            "max_attempts": 100,  # Максимум 100 попыток за неделю
        },
    },
    # ===== PROGRESSIVE DELAYS =====
    # Экспоненциальные задержки
    "enable_progressive_delays": True,
    "base_delay": 0.5,  # Базовая задержка (секунды)
    "max_delay": 30,  # Максимальная задержка (секунды)
    # ===== WHITELIST =====
    # IP адреса, которые не блокируются (для тестов)
    "whitelist_ips": [
        "127.0.0.1",
        "::1",
        # Добавьте свои доверенные IP
    ],
    # ===== BLACKLIST =====
    # IP адреса, которые блокируются навсегда
    "blacklist_ips": [
        # Добавьте известные вредоносные IP
    ],
}

# ============================================
# LOGGING
# ============================================

# LOGGING["loggers"]["security"] = {
#     "handlers": ["console", "security_file"],
#     "level": "INFO",
#     "propagate": False,
# }
#
# LOGGING["handlers"]["security_file"] = {
#     "level": "WARNING",
#     "class": "logging.handlers.RotatingFileHandler",
#     "filename": "logs/security_brute_force.log",
#     "formatter": "verbose_with_location",
#     "maxBytes": 1024 * 1024 * 15,  # 15 MB
#     "backupCount": 5,
# }
