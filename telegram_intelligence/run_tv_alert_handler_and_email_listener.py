import asyncio
import subprocess
import sys

async def run_handlers():
    # Запускаем tv_alert_handler.py в подпроцессе
    proc1 = await asyncio.create_subprocess_exec(
        sys.executable, 'tv_alert_relay/tv_alert_handler.py'
    )
    # Запускаем email_listener.py в подпроцессе
    proc2 = await asyncio.create_subprocess_exec(
        sys.executable, 'email_listener.py'
    )
    # Ждём завершения (они будут работать бесконечно)
    await asyncio.gather(proc1.wait(), proc2.wait())

if __name__ == '__main__':
    asyncio.run(run_handlers())