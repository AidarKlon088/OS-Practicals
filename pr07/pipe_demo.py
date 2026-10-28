#!/usr/bin/env python3
"""
PR7 — Неименованный канал (pipe) между родителем и потомком.

1. Родитель создаёт два канала и делает fork(). По первому каналу он отправляет
   потомку текст, по второму потомок возвращает статистику (строки, слова,
   символы) — как `wc`. Родитель сверяет ответ со своим подсчётом (assert).
2. Ёмкость канала: F_GETPIPE_SZ и заполнение канала в неблокирующем режиме.
3. Пропускная способность: потомок передаёт родителю 64 МБ.

Запуск:  python3 pipe_demo.py   (только Linux)
"""

import fcntl
import os
import select
import time

TEXT = """Операционная система управляет процессами.
Процессы обмениваются данными через каналы.
Канал — это буфер в ядре с двумя концами:
один для записи, другой для чтения.
"""
TOTAL_MB = 64
CHUNK = 64 * 1024


def wc(text):
    return len(text.splitlines()), len(text.split()), len(text)


def read_all(fd):
    chunks = []
    while True:
        chunk = os.read(fd, CHUNK)
        if not chunk:                 # 0 байт = EOF: все концы записи закрыты
            break
        chunks.append(chunk)
    return b"".join(chunks)


def demo_exchange():
    print("1. Обмен данными родитель <-> потомок")
    to_child_r, to_child_w = os.pipe()
    to_parent_r, to_parent_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        # потомок: закрываем ненужные концы, иначе EOF никогда не наступит
        os.close(to_child_w)
        os.close(to_parent_r)
        text = read_all(to_child_r).decode()
        os.close(to_child_r)
        lines, words, chars = wc(text)
        os.write(to_parent_w, f"{lines} {words} {chars}".encode())
        os.close(to_parent_w)
        os._exit(0)

    os.close(to_child_r)
    os.close(to_parent_w)
    print(f"  родитель PID={os.getpid()}, потомок PID={pid}")
    print(f"  дескрипторы: to_child=({to_child_r}, {to_child_w}), "
          f"to_parent=({to_parent_r}, {to_parent_w})")
    data = TEXT.encode()
    os.write(to_child_w, data)
    os.close(to_child_w)              # потомок увидит EOF
    print(f"  родитель отправил {len(data)} байт и закрыл конец записи")
    answer = read_all(to_parent_r).decode()
    os.close(to_parent_r)
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    expected = "%d %d %d" % wc(TEXT)
    print(f"  ответ потомка (строки слова символы): {answer}")
    print(f"  код завершения потомка: {code}")
    assert answer == expected, f"ожидалось {expected}, получено {answer}"
    assert code == 0
    print(f"  assert: ответ совпадает с подсчётом родителя ({expected}) — OK\n")


def demo_capacity():
    print("2. Ёмкость канала")
    r, w = os.pipe()
    size = fcntl.fcntl(w, fcntl.F_GETPIPE_SZ)
    os.set_blocking(w, False)
    block = b"x" * select.PIPE_BUF
    written = 0
    try:
        while True:
            written += os.write(w, block)
    except BlockingIOError:
        pass
    print(f"  F_GETPIPE_SZ = {size} байт, PIPE_BUF (атомарная запись) = {select.PIPE_BUF} байт")
    print(f"  записано без чтения (O_NONBLOCK): {written} байт, следующий write() -> BlockingIOError")
    print("  в обычном (блокирующем) режиме write() здесь заснул бы, пока кто-то не прочитает")
    assert written == size
    os.close(r)
    os.close(w)
    print("  assert: канал заполнился ровно на F_GETPIPE_SZ байт — OK\n")


def demo_throughput():
    total = TOTAL_MB * 1024 * 1024
    print(f"3. Передача {TOTAL_MB} МБ через канал (блоки по {CHUNK // 1024} КБ)")
    r, w = os.pipe()
    start = time.perf_counter()
    pid = os.fork()
    if pid == 0:
        os.close(r)
        block = b"\0" * CHUNK
        for _ in range(total // CHUNK):
            os.write(w, block)        # блокируется, пока в канале нет места
        os.close(w)
        os._exit(0)

    os.close(w)
    received = 0
    while chunk := os.read(r, CHUNK):
        received += len(chunk)
    os.close(r)
    os.waitpid(pid, 0)
    elapsed = time.perf_counter() - start
    print(f"  получено {received} байт за {elapsed:.3f} с — {TOTAL_MB / elapsed:.0f} МБ/с")
    assert received == total
    print("  assert: получены все байты — OK")


if __name__ == "__main__":
    demo_exchange()
    demo_capacity()
    demo_throughput()
