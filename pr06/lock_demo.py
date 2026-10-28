#!/usr/bin/env python3
"""
PR6 — Исправление гонки с помощью threading.Lock.

Сравниваются 4 варианта (4 потока x 100 000 инкрементов):
  1. counter += 1 без блокировки;
  2. counter += 1 внутри `with lock:`;
  3. чтение / sleep(0) / запись без блокировки (гонка из race_demo.py);
  4. то же самое внутри `with lock:` — гонки нет, хотя переключения остались.

Для вариантов с блокировкой проверяется assert counter == 400 000.
Каждый вариант запускается RUNS раз, печатается время.

Запуск:  python3 lock_demo.py
"""

import threading
import time

NUM_THREADS = 4
INCREMENTS = 100_000
EXPECTED = NUM_THREADS * INCREMENTS
RUNS = 3

counter = 0
lock = threading.Lock()


def plain_no_lock(i):
    global counter
    for _ in range(INCREMENTS):
        counter += 1


def plain_with_lock(i):
    global counter
    for _ in range(INCREMENTS):
        with lock:               # захват; освобождение — при выходе из блока
            counter += 1


def race_no_lock(i):
    global counter
    for _ in range(INCREMENTS):
        value = counter
        time.sleep(0)
        counter = value + 1


def race_with_lock(i):
    global counter
    for _ in range(INCREMENTS):
        with lock:               # чтение, переключение и запись — одна критическая секция
            value = counter
            time.sleep(0)
            counter = value + 1


def run(worker):
    global counter
    counter = 0
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_THREADS)]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counter, time.perf_counter() - start


def main():
    variants = [
        ("1. counter += 1, без Lock", plain_no_lock, False),
        ("2. counter += 1, with lock", plain_with_lock, True),
        ("3. read/sleep(0)/write, без Lock", race_no_lock, False),
        ("4. read/sleep(0)/write, with lock", race_with_lock, True),
    ]
    print(f"Потоков: {NUM_THREADS}, инкрементов на поток: {INCREMENTS}, ожидаемо: {EXPECTED}\n")
    summary = []
    for title, worker, must_be_exact in variants:
        print(title)
        times = []
        for r in range(1, RUNS + 1):
            result, elapsed = run(worker)
            times.append(elapsed)
            status = "OK" if result == EXPECTED else f"ПОТЕРЯНО {EXPECTED - result}"
            print(f"  запуск {r}: counter = {result:>6}  {status:<16} время = {elapsed:.3f} с")
            if must_be_exact:
                assert result == EXPECTED, f"с блокировкой ожидалось {EXPECTED}, получено {result}"
        avg = sum(times) / len(times)
        summary.append((title, avg))
        print(f"  среднее время: {avg:.3f} с\n")

    print("Итог (среднее время):")
    for title, avg in summary:
        print(f"  {title:<36} {avg:.3f} с")
    print(f"\nЗамедление из-за Lock (вариант 2 / вариант 1): {summary[1][1] / summary[0][1]:.1f}x")
    print("Все проверки assert для вариантов с Lock пройдены: counter == 400000")


if __name__ == "__main__":
    main()
