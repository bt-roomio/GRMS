import asyncio
from functools import wraps


def periodic_task():
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
