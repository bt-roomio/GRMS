import asyncio
import functools
import logging
from functools import wraps

logger = logging.getLogger("django")


def periodic_task_legacy():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, cmd, *args, **kwargs):
            task_key = f"cmd_id-{cmd.get('cmd_id')}"
            sleep_time = cmd.get("history_cmd", {}).get("time_window") or 5

            if self.tasks.get(task_key):
                await self.cancel_task(task_key)

            async def periodic_task_runner():
                return await func(self, cmd, *args, **kwargs)

            self.tasks[task_key] = {
                "func": periodic_task_runner,
                "stopped": False,
                "task": asyncio.create_task(self.send_periodic_data(periodic_task_runner, sleep_time)),
            }

        return wrapper

    return decorator


def periodic_task():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, cmd, *args, **kwargs):
            task_key = f"task-{cmd.get('cmd_id')}"
            sleep_time = cmd.get("history_cmd", {}).get("time_window") or 5

            # Если задача уже запущена, возвращаем её
            if task_key in self.tasks and not self.tasks[task_key].done():
                return self.tasks[task_key]

            async def periodic_loop():
                try:
                    while True:
                        try:
                            # Вызов обработчика
                            await func(self, cmd, *args, **kwargs)
                        except Exception as e:
                            logger.exception("Ошибка в периодическом задании '%s': %s", func.__name__, e)
                        # Задержка между вызовами
                        await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    logger.info("Периодическое задание '%s' отменено", func.__name__)
                    raise

            task = asyncio.create_task(periodic_loop())
            self.tasks[task_key] = task
            return task

        return wrapper

    return decorator
