#!/usr/bin/env python3
"""
PR7 — Именованный канал (FIFO), сторона чтения.

Создаёт FIFO (если его нет), открывает на чтение — open() блокируется, пока
не появится писатель, — печатает сообщения до EOF и удаляет FIFO.
Читатель и писатель — независимые программы, не родитель и потомок:
FIFO связывает их через имя в файловой системе.

Запуск (два терминала):
  python3 fifo_reader.py [путь]     # по умолчанию /tmp/pr07.fifo
  python3 fifo_writer.py [путь]
"""

import os
import stat
import sys
import time

PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pr07.fifo"


def log(msg):
    print(f"[reader] {msg}", flush=True)


def main():
    if not os.path.exists(PATH):
        os.mkfifo(PATH, 0o600)
    st = os.stat(PATH)
    assert stat.S_ISFIFO(st.st_mode), f"{PATH} существует, но это не FIFO"
    log(f"PID={os.getpid()} PPID={os.getppid()}, FIFO {PATH} ({stat.filemode(st.st_mode)})")
    log("open() на чтение — жду писателя...")
    start = time.perf_counter()
    count = 0
    with open(PATH, "r", encoding="utf-8") as fifo:
        log(f"писатель подключился, open() ждал {time.perf_counter() - start:.2f} с")
        for line in fifo:             # цикл закончится на EOF, когда писатель закроет FIFO
            count += 1
            log(f"получено: {line.rstrip()}")
    log(f"EOF, всего сообщений: {count}")
    os.unlink(PATH)
    log(f"FIFO удалён: exists = {os.path.exists(PATH)}")


if __name__ == "__main__":
    main()
