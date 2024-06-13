import asyncio


async def periodically_task(seconds: int, func, *args):
    while True:
        await func(*args)
        await asyncio.sleep(seconds)
