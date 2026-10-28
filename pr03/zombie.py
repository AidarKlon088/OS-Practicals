import os
import time

pid = os.fork()

if pid == 0:
    print(f"Дочерний PID={os.getpid()}", flush=True)
    os._exit(0)
else:
    print(f"Родитель PID={os.getpid()}", flush=True)
    print("Проверяй состояние ребёнка в течение 30 секунд")
    time.sleep(30)
    os.waitpid(pid, 0)
    print("Зомби-процесс исчез после waitpid()")