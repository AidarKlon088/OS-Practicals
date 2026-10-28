#!/usr/bin/env python3
"""
PR6 — Демонстрация гонки (код взят из pr04/threads_demo.py, режим race).

4 потока по 100 000 раз увеличивают общий counter БЕЗ блокировки.
Между чтением и записью стоит time.sleep(0) — явное переключение потоков,
поэтому потеря обновлений гарантированно видна.

Запуск:  python3 race_demo.py
"""

import threading
import time

NUM_THREADS = 4
INCREMENTS = 100_000
RUNS = 3

counter = 0


def worker(i):
    global counter
    for _ in range(INCREMENTS):
        value = counter      # чтение
        time.sleep(0)        # переключение на другой поток
        counter = value + 1  # запись устаревшего значения -> гонка


def run_once():
    global counter
    counter = 0
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counter


if __name__ == "__main__":
    expected = NUM_THREADS * INCREMENTS
    print(f"Без блокировки, ожидаемо {expected}")
    for run in range(1, RUNS + 1):
        start = time.perf_counter()
        result = run_once()
        print(f"Запуск {run}: counter = {result}, потеряно {expected - result}, "
              f"время {time.perf_counter() - start:.3f} с")
