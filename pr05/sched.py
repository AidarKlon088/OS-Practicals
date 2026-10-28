#!/usr/bin/env python3
"""
PR5 — Симулятор планирования CPU (вариант A): FCFS, SJF (невытесняющий), RR.

Формат входного файла (одна строка — один процесс):
    PID arrival burst priority
Пустые строки и строки, начинающиеся с '#', пропускаются.
Поле priority читается, но алгоритмами варианта A не используется.

Соглашения (правила разрешения равенств):
  * FCFS: порядок по времени прихода; при равном arrival — порядок в файле.
  * SJF:  из пришедших процессов выбирается наименьший burst;
          при равном burst — меньший arrival, затем порядок в файле.
  * RR:   очередь FIFO. Если в момент окончания кванта приходят новые
          процессы, они встают в очередь РАНЬШЕ процесса, у которого
          закончился квант (сначала новые, потом вытесненный).
  * Если готовых процессов нет, CPU простаивает (в диаграмме — "idle").

Метрики:
  turnaround (время оборота) = completion - arrival
  waiting    (время ожидания) = turnaround - burst

Примеры запуска:
  python3 sched.py --algo fcfs set1.txt
  python3 sched.py --algo sjf set1.txt
  python3 sched.py --algo rr --quantum 3 set1.txt
  python3 sched.py --compare --quantum 3 set1.txt set2.txt set3.txt
"""

import argparse
from collections import deque


class Process:
    def __init__(self, pid, arrival, burst, priority, order):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.priority = priority
        self.order = order        # номер строки в файле (для равенств)
        self.completion = None    # время завершения, заполняет алгоритм


def read_processes(path):
    """Читает файл формата 'PID arrival burst priority'."""
    processes = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 4:
                raise ValueError(f"{path}:{line_no}: ожидалось 4 поля, получено {len(parts)}")
            pid, arrival, burst, priority = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            if arrival < 0 or burst <= 0:
                raise ValueError(f"{path}:{line_no}: arrival >= 0 и burst > 0")
            processes.append(Process(pid, arrival, burst, priority, len(processes)))
    if not processes:
        raise ValueError(f"{path}: нет процессов")
    return processes


def add_slice(gantt, name, start, end):
    """Добавляет отрезок в диаграмму Ганта, склеивая соседние одинаковые."""
    if gantt and gantt[-1][0] == name and gantt[-1][2] == start:
        gantt[-1] = (name, gantt[-1][1], end)
    else:
        gantt.append((name, start, end))


def fcfs(processes):
    gantt = []
    time = 0
    for p in sorted(processes, key=lambda p: (p.arrival, p.order)):
        if time < p.arrival:                 # CPU простаивает до прихода
            add_slice(gantt, "idle", time, p.arrival)
            time = p.arrival
        add_slice(gantt, p.pid, time, time + p.burst)
        time += p.burst
        p.completion = time
    return gantt


def sjf(processes):
    gantt = []
    time = 0
    remaining = list(processes)
    while remaining:
        ready = [p for p in remaining if p.arrival <= time]
        if not ready:                        # никто ещё не пришёл
            next_arrival = min(p.arrival for p in remaining)
            add_slice(gantt, "idle", time, next_arrival)
            time = next_arrival
            continue
        p = min(ready, key=lambda p: (p.burst, p.arrival, p.order))
        add_slice(gantt, p.pid, time, time + p.burst)
        time += p.burst                      # невытесняющий: работает до конца
        p.completion = time
        remaining.remove(p)
    return gantt


def rr(processes, quantum):
    gantt = []
    time = 0
    incoming = deque(sorted(processes, key=lambda p: (p.arrival, p.order)))
    left = {p.pid: p.burst for p in processes}   # оставшееся время
    queue = deque()

    def admit(up_to):
        """Переносит в очередь все процессы, пришедшие к моменту up_to."""
        while incoming and incoming[0].arrival <= up_to:
            queue.append(incoming.popleft())

    admit(time)
    while queue or incoming:
        if not queue:                        # очередь пуста — простой
            add_slice(gantt, "idle", time, incoming[0].arrival)
            time = incoming[0].arrival
            admit(time)
            continue
        p = queue.popleft()
        run = min(quantum, left[p.pid])
        add_slice(gantt, p.pid, time, time + run)
        time += run
        left[p.pid] -= run
        admit(time)                          # сначала новые процессы...
        if left[p.pid] > 0:
            queue.append(p)                  # ...потом вытесненный
        else:
            p.completion = time
    return gantt


def metrics(processes):
    """Возвращает список (pid, arrival, burst, completion, tat, wt) и средние."""
    rows = []
    for p in sorted(processes, key=lambda p: p.order):
        tat = p.completion - p.arrival
        wt = tat - p.burst
        rows.append((p.pid, p.arrival, p.burst, p.completion, tat, wt))
    avg_tat = sum(r[4] for r in rows) / len(rows)
    avg_wt = sum(r[5] for r in rows) / len(rows)
    return rows, avg_wt, avg_tat


def simulate(path, algo, quantum):
    processes = read_processes(path)
    if algo == "fcfs":
        gantt = fcfs(processes)
    elif algo == "sjf":
        gantt = sjf(processes)
    else:
        gantt = rr(processes, quantum)
    rows, avg_wt, avg_tat = metrics(processes)
    return gantt, rows, avg_wt, avg_tat


def gantt_text(gantt):
    """Текстовая диаграмма Ганта: ширина ячейки пропорциональна длительности."""
    bar, scale = "|", ""
    for name, start, end in gantt:
        width = max(len(name) + 2, (end - start) * 2)
        bar += name.center(width) + "|"
        scale += str(start).ljust(width + 1)
    scale += str(gantt[-1][2])
    return bar + "\n" + scale


def print_report(path, algo, quantum):
    gantt, rows, avg_wt, avg_tat = simulate(path, algo, quantum)
    title = algo.upper() + (f" (quantum = {quantum})" if algo == "rr" else "")
    print(f"=== {title}: {path} ===")
    print("Диаграмма Ганта:")
    print(gantt_text(gantt))
    print()
    print(f"{'PID':<5}{'Arrival':>8}{'Burst':>7}{'Finish':>8}{'TAT':>6}{'WT':>6}")
    for pid, arrival, burst, completion, tat, wt in rows:
        print(f"{pid:<5}{arrival:>8}{burst:>7}{completion:>8}{tat:>6}{wt:>6}")
    print(f"Среднее время ожидания (WT):  {avg_wt:.2f}")
    print(f"Среднее время оборота  (TAT): {avg_tat:.2f}")
    print()


def print_compare(paths, quantum):
    print(f"Сравнение алгоритмов (RR quantum = {quantum})")
    print(f"{'Набор':<10}{'Алгоритм':<10}{'Avg WT':>8}{'Avg TAT':>9}")
    for path in paths:
        for algo in ("fcfs", "sjf", "rr"):
            _, _, avg_wt, avg_tat = simulate(path, algo, quantum)
            print(f"{path:<10}{algo.upper():<10}{avg_wt:>8.2f}{avg_tat:>9.2f}")


def main():
    parser = argparse.ArgumentParser(description="Симулятор планирования CPU")
    parser.add_argument("files", nargs="+", help="файлы с процессами")
    parser.add_argument("--algo", choices=["fcfs", "sjf", "rr"], default="fcfs")
    parser.add_argument("--quantum", type=int, default=3, help="квант для RR")
    parser.add_argument("--compare", action="store_true",
                        help="таблица сравнения всех алгоритмов по всем файлам")
    args = parser.parse_args()
    if args.quantum <= 0:
        parser.error("квант должен быть положительным")

    if args.compare:
        print_compare(args.files, args.quantum)
    else:
        for path in args.files:
            print_report(path, args.algo, args.quantum)


if __name__ == "__main__":
    main()
