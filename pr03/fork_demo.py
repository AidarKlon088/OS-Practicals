import os
import sys

pid = os.fork()

if pid == 0:
    print(f"Я ребёнок, PID={os.getpid()}, PPID={os.getppid()}")
    sys.exit(0)
else:
    print(f"Я родитель, PID={os.getpid()}")

    child_pid, status = os.wait()
    exit_code = os.waitstatus_to_exitcode(status)

    print(f"Ребёнок {child_pid} завершился с кодом {exit_code}")