#!/usr/bin/env python3
"""
PR4 — Потоки в Linux (вариант A).

Программа:
  1. Создаёт 4 потока через threading.Thread(target=worker, args=(i,)).
  2. Каждый поток 100 000 раз увеличивает общую переменную counter.
  3. Делает 5 запусков и печатает результат каждого запуска.
  4. Показывает число потоков процесса через /proc/PID/status и /proc/PID/task.

Режимы (ключ --mode):
  plain - обычное counter += 1 (без блокировки);
  race  - чтение и запись разделены явным переключением потоков
          (time.sleep(0)), поэтому гонка гарантированно видна.

Запуск:
  python3 threads_demo.py               # режим race, 5 запусков + /proc
  python3 threads_demo.py --mode plain  # обычный инкремент
"""

import argparse
import os
import threading
import time

NUM_THREADS = 4          # количество потоков
INCREMENTS = 100_000     # сколько раз каждый поток увеличивает counter
RUNS = 5                 # количество запусков

counter = 0              # общая (разделяемая) переменная


def worker_plain(i):
    """Обычный инкремент без блокировки."""
    global counter
    for _ in range(INCREMENTS):
        counter += 1


def worker_race(i):
    """
    Инкремент, разбитый на три шага: прочитать -> уступить CPU -> записать.
    time.sleep(0) отдаёт процессор другому потоку как раз между чтением
    и записью. Другой поток успевает изменить counter, а мы потом
    записываем устаревшее значение, — так теряются обновления (гонка).
    """
    global counter
    for _ in range(INCREMENTS):
        value = counter      # 1. чтение
        time.sleep(0)        # 2. явное переключение на другой поток
        counter = value + 1  # 3. запись (возможно, уже устаревшего значения)


def run_once(worker):
    """Один запуск: создать 4 потока, дождаться их и вернуть counter."""
    global counter
    counter = 0
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    return counter


def show_proc_threads():
    """
    Запускаем 4 «спящих» потока и смотрим, сколько потоков видит ядро
    в /proc/PID/status (строка Threads) и в каталоге /proc/PID/task.
    Каждый поток Python — это отдельная задача ядра Linux со своим TID.
    """
    stop = threading.Event()
    threads = [threading.Thread(target=stop.wait, name=f"sleeper-{i}")
               for i in range(NUM_THREADS)]
    for t in threads:
        t.start()

    pid = os.getpid()
    with open(f"/proc/{pid}/status") as f:
        threads_line = [line.strip() for line in f if line.startswith("Threads:")][0]
    tids = sorted(os.listdir(f"/proc/{pid}/task"), key=int)

    print(f"PID процесса: {pid}")
    print(f"/proc/{pid}/status -> {threads_line}")
    print(f"/proc/{pid}/task   -> {len(tids)} записей: {' '.join(tids)}")
    print("(1 главный поток + 4 рабочих потока)")

    stop.set()
    for t in threads:
        t.join()


def main():
    parser = argparse.ArgumentParser(description="PR4: потоки и гонка данных")
    parser.add_argument("--mode", choices=["race", "plain"], default="race",
                        help="race - с явным переключением, plain - counter += 1")
    args = parser.parse_args()
    worker = worker_race if args.mode == "race" else worker_plain
    expected = NUM_THREADS * INCREMENTS

    print(f"Режим: {args.mode}; потоков: {NUM_THREADS}; "
          f"инкрементов на поток: {INCREMENTS}; ожидаемо: {expected}")
    for run in range(1, RUNS + 1):
        start = time.perf_counter()
        result = run_once(worker)
        elapsed = time.perf_counter() - start
        lost = expected - result
        print(f"Запуск {run}: counter = {result:>7}  потеряно = {lost:>7}  "
              f"время = {elapsed:.3f} с")

    print()
    show_proc_threads()


if __name__ == "__main__":
    main()
