"""
Redis-based brute force protection для REST API
"""

import hashlib
import json
import logging
import time
from typing import Dict, Tuple

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Используем отдельный Redis cache для security
security_cache = caches["security"]


class APIBruteForceProtectionMiddleware(MiddlewareMixin):
    """
    Middleware для защиты API endpoints от brute force атак

    Особенности:
    - Работает со ВСЕМИ API endpoints
    - Использует Redis (быстро)
    - Многоуровневая защита
    - Не требует декораторов
    - CAPTCHA (Cloudflare Turnstile) после N неудачных попыток
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

        # Загрузить конфигурацию
        self.config = getattr(settings, "BRUTE_FORCE_CONFIG", {})

        # Endpoints для защиты
        self.protected_endpoints = self.config.get(
            "protected_endpoints",
            [
                "/api/auth/login/",
                "/api/auth/token/",
                "/api/v1/auth/login/",
            ],
        )

        # Лимиты
        self.max_attempts = self.config.get("max_attempts", 5)
        self.lockout_duration = self.config.get("lockout_duration", 900)  # 15 минут
        self.attempt_window = self.config.get("attempt_window", 300)  # 5 минут

        # Расширенные временные окна
        self.time_windows = self.config.get(
            "time_windows",
            {
                "1h": {"duration": 3600, "max_attempts": 10},
                "24h": {"duration": 86400, "max_attempts": 30},
            },
        )

        # Progressive delays
        self.enable_progressive_delays = self.config.get("enable_progressive_delays", True)
        self.base_delay = self.config.get("base_delay", 0.5)
        self.max_delay = self.config.get("max_delay", 30)

        # CAPTCHA (Cloudflare Turnstile)
        self.captcha_enabled = self.config.get("captcha_enabled", False)
        self.captcha_threshold = self.config.get("captcha_threshold", 3)

        # Whitelist / blacklist из конфига
        self.whitelist_ips = set(self.config.get("whitelist_ips", []))
        self.blacklist_ips = set(self.config.get("blacklist_ips", []))

    def process_request(self, request):
        """Проверить перед обработкой запроса"""

        # Проверить только защищенные endpoints
        if not self._should_protect(request):
            return None

        # Получить идентификаторы
        ip = self._get_client_ip(request)

        # Whitelist — доверенные IP не проходят защиту (тесты, внутренние сервисы)
        if ip in self.whitelist_ips:
            return None

        # Blacklist — заблокированные IP отклоняются немедленно
        if ip in self.blacklist_ips:
            logger.warning(f"Blacklisted IP blocked: {ip} (path: {request.path})")
            return self._blocked_response("IP blacklisted")

        body_data = self._parse_request_body(request)
        email = body_data.get("email", "anonymous")

        # Проверить блокировку
        is_blocked, block_reason = self._check_lockout(ip, email)

        if is_blocked:
            logger.warning(
                f"Blocked request: {request.method} {request.path} " f"from {ip} (email: {email}) - {block_reason}"
            )

            return self._blocked_response(block_reason)

        # Проверить CAPTCHA
        if self.captcha_enabled:
            captcha_response = self._check_captcha(ip, email, captcha_token=body_data.get("captcha_token"))
            if captcha_response is not None:
                return captcha_response

        # Применить progressive delay
        if self.enable_progressive_delays:
            delay = self._get_progressive_delay(ip, email)
            if delay > 0:
                time.sleep(delay)

        # Сохранить данные в request для использования в response
        request._bf_ip = ip
        request._bf_email = email
        request._bf_start_time = time.time()

        return None

    def process_response(self, request, response):
        """Обработать после получения ответа"""

        # Проверить только защищенные endpoints
        if not self._should_protect(request):
            return response

        # Получить сохраненные данные
        ip = getattr(request, "_bf_ip", None)
        email = getattr(request, "_bf_email", None)

        if not ip or not email:
            return response

        # Определить успех/неудачу по статус коду.
        # 429 (throttle) тоже считается неудачной попыткой — иначе атакующий
        # остаётся ниже порога lockout, чередуя throttled-запросы.
        is_success = response.status_code in [200, 201]
        is_failure = response.status_code in [401, 403, 429]

        if is_failure:
            # Записать неудачную попытку
            self._record_failed_attempt(ip, email, request)

            # Добавить информацию об оставшихся попытках
            attempts_left = self._get_attempts_left(ip, email)

            # Если response - JSON, добавить информацию
            if response.get("Content-Type", "").startswith("application/json"):
                try:
                    data = json.loads(response.content)
                    data["attempts_left"] = attempts_left
                    data["lockout_duration"] = self.lockout_duration

                    # Добавить информацию о CAPTCHA
                    if self.captcha_enabled:
                        requires_captcha = self._requires_captcha(ip, email)
                        data["captcha_required"] = requires_captcha
                        if requires_captcha:
                            data["captcha_site_key"] = getattr(settings, "TURNSTILE_SITE_KEY", "")

                    response.content = json.dumps(data).encode()
                except Exception:
                    pass

        elif is_success:
            # Сбросить счетчики при успехе
            self._reset_attempts(ip, email)

        return response

    def _should_protect(self, request) -> bool:
        """Определить, нужно ли защищать этот endpoint"""

        # Проверить метод (защищаем только POST)
        if request.method != "POST":
            return False

        # Проверить путь
        path = request.path

        # Точное совпадение
        if path in self.protected_endpoints:
            return True

        # Паттерны (можно расширить)
        protected_patterns = [
            "/api/auth/",
            "/api/v1/auth/",
            "/api/v1/users/access-token/",
        ]

        return any(pattern in path for pattern in protected_patterns)

    def _get_client_ip(self, request) -> str:
        """Получить реальный IP клиента"""
        # Cloudflare
        ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if ip:
            return ip

        # X-Forwarded-For
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        # X-Real-IP
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip

        # Обычный REMOTE_ADDR
        return request.META.get("REMOTE_ADDR", "unknown")

    def _parse_request_body(self, request) -> dict:
        """Парсинг JSON body из запроса (один раз)"""
        try:
            if request.body:
                return json.loads(request.body)
        except Exception:
            pass
        return {}

    def _check_lockout(self, ip: str, email: str) -> Tuple[bool, str]:
        """
        Проверить блокировку на разных уровнях
        Returns: (is_blocked, reason)
        """

        # Уровень 1: Жесткая блокировка (ручная или автоматическая)
        hard_block_key = f"bf:hard_block:{self._hash(ip)}"
        if security_cache.get(hard_block_key):
            return True, "IP permanently blocked"

        # Уровень 2: Временная блокировка (после превышения лимита)
        lockout_key = f"bf:lockout:{self._hash(f'{email}:{ip}')}"
        lockout_until = security_cache.get(lockout_key)

        if lockout_until:
            remaining = int(lockout_until) - int(time.time())
            if remaining > 0:
                return True, f"Too many failed attempts. Try again in {remaining} seconds"

        # Уровень 3: Проверка расширенных временных окон
        for window_name, window_config in self.time_windows.items():
            if self._check_extended_window(ip, email, window_name, window_config):
                return True, f"Too many attempts in {window_name} period"

        return False, ""

    def _check_extended_window(self, ip: str, email: str, window_name: str, window_config: Dict) -> bool:
        """Проверить расширенное временное окно"""

        key = f"bf:window:{window_name}:{self._hash(f'{email}:{ip}')}"
        attempts = security_cache.get(key, [])

        # Очистить старые записи
        cutoff = time.time() - window_config["duration"]
        attempts = [a for a in attempts if a["time"] > cutoff]

        # Подсчитать неудачные попытки
        failed_attempts = [a for a in attempts if not a.get("success", False)]

        # Проверить лимит
        if len(failed_attempts) >= window_config["max_attempts"]:
            logger.critical(
                f"Extended window limit exceeded: {len(failed_attempts)} attempts "
                f"in {window_name} for {email} from {ip}"
            )
            return True

        return False

    # ==========================================
    # CAPTCHA (Cloudflare Turnstile)
    # ==========================================

    def _get_attempt_count(self, ip: str, email: str) -> int:
        """Получить текущее количество попыток из Redis"""
        attempt_key = f"bf:attempts:{self._hash(f'{email}:{ip}')}"
        return security_cache.get(attempt_key, 0)

    def _requires_captcha(self, ip: str, email: str) -> bool:
        """Проверить, требуется ли CAPTCHA на основе количества попыток"""
        if not self.captcha_enabled:
            return False
        return self._get_attempt_count(ip, email) >= self.captcha_threshold

    def _check_captcha(self, ip: str, email: str, captcha_token: str | None = None):
        """
        Валидация CAPTCHA токена если требуется.

        Returns None если CAPTCHA не требуется или токен валиден.
        Returns JsonResponse если CAPTCHA требуется но отсутствует/невалиден.
        """
        if not self._requires_captcha(ip, email):
            return None

        if not captcha_token:
            logger.warning(f"CAPTCHA required but not provided: {email} from {ip}")
            return JsonResponse(
                {
                    "error": "CAPTCHA required",
                    "detail": "Too many failed attempts. Please complete the CAPTCHA challenge.",
                    "captcha_required": True,
                    "captcha_site_key": getattr(settings, "TURNSTILE_SITE_KEY", ""),
                },
                status=403,
            )

        # Верифицировать токен через Cloudflare API
        from core.utils.turnstile import TurnstileVerificationError, verify_turnstile_token

        try:
            is_valid = verify_turnstile_token(captcha_token, remote_ip=ip)
        except TurnstileVerificationError:
            # Fail open при проблемах с инфраструктурой — brute force защита всё ещё активна
            logger.error(f"Turnstile verification failed (infrastructure), allowing request: {email} from {ip}")
            return None

        if not is_valid:
            logger.warning(f"Invalid CAPTCHA token: {email} from {ip}")
            return JsonResponse(
                {
                    "error": "Invalid CAPTCHA",
                    "detail": "CAPTCHA verification failed. Please try again.",
                    "captcha_required": True,
                    "captcha_site_key": getattr(settings, "TURNSTILE_SITE_KEY", ""),
                },
                status=403,
            )

        # CAPTCHA валидна — пропускаем запрос
        return None

    # ==========================================
    # Attempt tracking
    # ==========================================

    def _record_failed_attempt(self, ip: str, email: str, request):
        """Записать неудачную попытку"""

        timestamp = time.time()

        # Основной ключ для подсчета попыток (используем простой счетчик)
        attempt_key = f"bf:attempts:{self._hash(f'{email}:{ip}')}"

        # Атомарный инкремент счетчика
        try:
            attempt_count = security_cache.incr(attempt_key)
            # Обновить TTL при каждой попытке
            try:
                security_cache.touch(attempt_key, self.attempt_window)
            except AttributeError:
                # touch не поддерживается, пересоздаем с новым TTL
                security_cache.set(attempt_key, attempt_count, self.attempt_window)
        except ValueError:
            # Ключ не существует, создаем
            security_cache.set(attempt_key, 1, self.attempt_window)
            attempt_count = 1

        # Проверить лимит для основного окна
        if attempt_count >= self.max_attempts:
            # БЛОКИРОВКА
            lockout_key = f"bf:lockout:{self._hash(f'{email}:{ip}')}"
            lockout_until = int(timestamp) + self.lockout_duration
            security_cache.set(lockout_key, lockout_until, self.lockout_duration)

            logger.critical(f"LOCKOUT TRIGGERED: {email} from {ip} - {attempt_count} failed attempts")

        # Записать в расширенные окна
        for window_name, window_config in self.time_windows.items():
            window_key = f"bf:window:{window_name}:{self._hash(f'{email}:{ip}')}"
            window_attempts = security_cache.get(window_key, [])

            window_attempts.append({"time": timestamp, "success": False})

            # Очистить старые
            cutoff = timestamp - window_config["duration"]
            window_attempts = [a for a in window_attempts if a["time"] > cutoff]

            security_cache.set(window_key, window_attempts, window_config["duration"])

        # Логирование
        logger.warning(f"Failed login attempt #{attempt_count}: {email} from {ip} (path: {request.path})")

        # Инкрементировать счетчик для progressive delay
        if self.enable_progressive_delays:
            delay_key = f"bf:delay:{self._hash(f'{email}:{ip}')}"
            current_count = security_cache.get(delay_key, 0)
            security_cache.set(delay_key, current_count + 1, self.attempt_window)

    def _reset_attempts(self, ip: str, email: str):
        """Сбросить счетчики при успешном входе"""

        # Основной ключ
        attempt_key = f"bf:attempts:{self._hash(f'{email}:{ip}')}"
        security_cache.delete(attempt_key)

        # Lockout ключ
        lockout_key = f"bf:lockout:{self._hash(f'{email}:{ip}')}"
        security_cache.delete(lockout_key)

        # Progressive delay ключ
        delay_key = f"bf:delay:{self._hash(f'{email}:{ip}')}"
        security_cache.delete(delay_key)

        logger.info(f"Successful login: {email} from {ip} - counters reset")

    def _get_attempts_left(self, ip: str, email: str) -> int:
        """Получить количество оставшихся попыток"""

        attempt_key = f"bf:attempts:{self._hash(f'{email}:{ip}')}"
        attempt_count = security_cache.get(attempt_key, 0)

        return max(0, self.max_attempts - attempt_count)

    def _get_progressive_delay(self, ip: str, email: str) -> float:
        """Получить задержку (exponential backoff)"""

        delay_key = f"bf:delay:{self._hash(f'{email}:{ip}')}"
        failure_count = security_cache.get(delay_key, 0)

        if failure_count == 0:
            return 0

        # Exponential: 2^n секунд
        delay = min(self.base_delay * (2**failure_count), self.max_delay)

        return delay

    def _blocked_response(self, reason: str) -> JsonResponse:
        """Ответ при блокировке"""

        return JsonResponse({"error": "Access denied", "detail": reason, "status": "blocked"}, status=429)

    def _hash(self, value: str) -> str:
        """Хеш для ключей Redis"""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
