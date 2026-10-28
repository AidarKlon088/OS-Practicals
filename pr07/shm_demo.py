#!/usr/bin/env python3
"""
PR7 — Разделяемая память между процессами.

0. Обычная глобальная переменная НЕ общая: у каждого процесса своё адресное
   пространство, изменения потомков родитель не видит.
1. Сегмент multiprocessing.shared_memory — в Linux это файл в /dev/shm,
   который несколько процессов отображают в свою память.
2. 4 процесса по 50 000 раз увеличивают общий 8-байтовый счётчик:
     * без блокировки — процессы работают на разных ядрах действительно
       параллельно (GIL у каждого свой), обновления теряются даже без sleep(0);
     * с multiprocessing.Lock (межпроцессный семафор) — результат точный.

Запуск:  python3 shm_demo.py   (только Linux)
"""

import multiprocessing
import os
import struct
import time
from multiprocessing import Lock, Process, shared_memory

PROCS = 4
INCREMENTS = 50_000
EXPECTED = PROCS * INCREMENTS
RUNS = 3

plain_counter = 0


def plain_worker():
    global plain_counter
    for _ in range(1000):
        plain_counter += 1
    print(f"  [процесс {os.getpid()}] своя копия plain_counter = {plain_counter}", flush=True)


def increment(shm):
    value = struct.unpack_from("q", shm.buf, 0)[0]   # чтение из общей памяти
    struct.pack_into("q", shm.buf, 0, value + 1)      # запись


def shm_worker(name, lock):
    shm = shared_memory.SharedMemory(name=name, track=False)   # подключение к сегменту
    for _ in range(INCREMENTS):
        if lock is None:
            increment(shm)
        else:
            with lock:
                increment(shm)
    shm.close()


def run(lock):
    shm = shared_memory.SharedMemory(create=True, size=8)
    try:
        struct.pack_into("q", shm.buf, 0, 0)
        procs = [Process(target=shm_worker, args=(shm.name, lock)) for _ in range(PROCS)]
        start = time.perf_counter()
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        elapsed = time.perf_counter() - start
        assert all(p.exitcode == 0 for p in procs)
        return struct.unpack_from("q", shm.buf, 0)[0], elapsed
    finally:
        shm.close()
        shm.unlink()


def main():
    print(f"Метод запуска процессов: {multiprocessing.get_start_method()}, ядер: {os.cpu_count()}\n")

    print("0. Обычная глобальная переменная")
    procs = [Process(target=plain_worker) for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    print(f"  в родителе plain_counter = {plain_counter} (изменения потомков не видны)")
    assert plain_counter == 0
    print()

    print("1. Сегмент разделяемой памяти")
    shm = shared_memory.SharedMemory(create=True, size=8)
    path = f"/dev/shm/{shm.name}"
    print(f"  создан сегмент {shm.name}: {path} существует = {os.path.exists(path)}, "
          f"размер = {os.stat(path).st_size} байт")
    shm.close()
    shm.unlink()
    print(f"  после unlink(): существует = {os.path.exists(path)}\n")

    print(f"2. Общий счётчик: {PROCS} процесса x {INCREMENTS} инкрементов, ожидаемо {EXPECTED}")
    summary = []
    for title, lock in [("без Lock", None), ("с multiprocessing.Lock", Lock())]:
        print(f"  {title}")
        times = []
        for r in range(1, RUNS + 1):
            result, elapsed = run(lock)
            times.append(elapsed)
            status = "OK" if result == EXPECTED else f"ПОТЕРЯНО {EXPECTED - result}"
            print(f"    запуск {r}: counter = {result:>6}  {status:<16} время = {elapsed:.3f} с")
            if lock is not None:
                assert result == EXPECTED, f"с Lock ожидалось {EXPECTED}, получено {result}"
        summary.append((title, sum(times) / len(times)))

    print("\nСреднее время:")
    for title, avg in summary:
        print(f"  {title:<24} {avg:.3f} с")
    print(f"Замедление из-за Lock: {summary[1][1] / summary[0][1]:.1f}x")
    print("assert: с Lock счётчик всегда равен 200000 — OK")


if __name__ == "__main__":
    main()
