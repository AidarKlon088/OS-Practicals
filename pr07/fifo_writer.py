#!/usr/bin/env python3
"""
PR7 — Именованный канал (FIFO), сторона записи.

Ждёт, пока fifo_reader.py создаст FIFO, открывает его на запись и отправляет
MESSAGES строк с паузой DELAY. Закрытие FIFO даёт читателю EOF.

Запуск:  python3 fifo_writer.py [путь]   # по умолчанию /tmp/pr07.fifo
"""

import os
import stat
import sys
import time

PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pr07.fifo"
MESSAGES = 5
DELAY = 0.2


def log(msg):
    print(f"[writer] {msg}", flush=True)


def fifo_exists():
    try:
        return stat.S_ISFIFO(os.stat(PATH).st_mode)
    except FileNotFoundError:
        return False


def main():
    for _ in range(50):
        if fifo_exists():
            break
        time.sleep(0.1)
    else:
        sys.exit(f"FIFO {PATH} не найден — сначала запустите fifo_reader.py")

    log(f"PID={os.getpid()} PPID={os.getppid()}, открываю {PATH} на запись")
    with open(PATH, "w", encoding="utf-8") as fifo:
        for i in range(1, MESSAGES + 1):
            msg = f"сообщение {i} от PID {os.getpid()} в {time.strftime('%H:%M:%S')}"
            fifo.write(msg + "\n")
            fifo.flush()              # без flush строка осталась бы в буфере Python
            log(f"отправлено: {msg}")
            time.sleep(DELAY)
    log("FIFO закрыт — читатель получит EOF")


if __name__ == "__main__":
    main()
