#!/usr/bin/env python3
"""
PR8 — Алгоритм банкира (избежание) и алгоритм обнаружения взаимоблокировок.

  is_safe()           — алгоритм безопасности: ищет безопасную последовательность;
  request_resources() — выдать ресурсы, только если система останется в
                        безопасном состоянии;
  detect_deadlock()   — обнаружение: какие процессы уже заблокированы
                        (по матрице текущих запросов Request).

Данные — классические примеры из учебника Silberschatz «Operating System
Concepts» (гл. 8), чтобы результат можно было сверить.

Запуск:  python3 bankers.py
"""

RESOURCES = "ABC"


def le(a, b):
    return all(x <= y for x, y in zip(a, b))


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def need_matrix(maximum, alloc):
    return [sub(m, a) for m, a in zip(maximum, alloc)]


def is_safe(available, maximum, alloc):
    """Возвращает (безопасно?, последовательность, шаги [(процесс, Work после него)])."""
    need = need_matrix(maximum, alloc)
    work = list(available)
    finish = [False] * len(alloc)
    seq, steps = [], []
    progress = True
    while progress:
        progress = False
        for i in range(len(alloc)):
            if not finish[i] and le(need[i], work):
                work = add(work, alloc[i])   # процесс завершится и вернёт всё, что держит
                finish[i] = True
                seq.append(i)
                steps.append((i, work))
                progress = True
    return all(finish), seq, steps


def request_resources(pid, req, available, maximum, alloc):
    """Возвращает (выдано?, причина отказа, (новые available, alloc, последовательность))."""
    need = need_matrix(maximum, alloc)
    if not le(req, need[pid]):
        return False, "ошибка: запрос больше объявленной потребности (Need)", None
    if not le(req, available):
        return False, "ресурсов недостаточно — процесс ждёт", None
    new_available = sub(available, req)
    new_alloc = [list(row) for row in alloc]
    new_alloc[pid] = add(new_alloc[pid], req)
    safe, seq, _ = is_safe(new_available, maximum, new_alloc)
    if not safe:
        return False, "состояние стало бы небезопасным — запрос отложен", None
    return True, "", (new_available, new_alloc, seq)


def detect_deadlock(available, alloc, request):
    """Возвращает (заблокированные процессы, порядок, в котором остальные могут завершиться)."""
    work = list(available)
    finish = [not any(a) for a in alloc]     # процесс без ресурсов никого не блокирует
    seq = []
    progress = True
    while progress:
        progress = False
        for i in range(len(alloc)):
            if not finish[i] and le(request[i], work):
                work = add(work, alloc[i])
                finish[i] = True
                seq.append(i)
                progress = True
    return [i for i, done in enumerate(finish) if not done], seq


def names(pids):
    return "<" + ", ".join(f"P{i}" for i in pids) + ">"


def vec(v):
    return " ".join(f"{x:>2}" for x in v)


def print_table(columns, rows_count):
    letters = " ".join(f"{r:>2}" for r in RESOURCES)
    widths = [max(len(title), len(letters)) for title, _ in columns]

    def line(cells):
        return "   ".join(cell.ljust(w) for cell, w in zip(cells, widths)).rstrip()

    print("      " + line([title for title, _ in columns]))
    print("      " + line([letters] * len(columns)))
    for i in range(rows_count):
        print(f"  P{i}  " + line([vec(matrix[i]) for _, matrix in columns]))


def print_state(available, maximum, alloc):
    print_table([("Allocation", alloc), ("Max", maximum),
                 ("Need", need_matrix(maximum, alloc))], len(alloc))
    print(f"  Available: {vec(available)}")


def show_safety(available, maximum, alloc):
    safe, seq, steps = is_safe(available, maximum, alloc)
    for pid, work in steps:
        print(f"    P{pid}: Need <= Work -> завершается, Work = {vec(work)}")
    print(f"  безопасно: {safe}, последовательность {names(seq)}")
    return safe, seq


def main():
    # Silberschatz, пример алгоритма банкира: A=10, B=5, C=7 экземпляров
    total = [10, 5, 7]
    alloc = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
    maximum = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
    available = sub(total, [sum(col) for col in zip(*alloc)])

    print(f"1. Алгоритм банкира. Всего ресурсов {RESOURCES}: {vec(total)}")
    print_state(available, maximum, alloc)
    show_safety(available, maximum, alloc)

    print("\n2. Запрос P1 (1, 0, 2)")
    ok, reason, result = request_resources(1, [1, 0, 2], available, maximum, alloc)
    print(f"  выдано: {ok}")
    available, alloc, _ = result
    print_state(available, maximum, alloc)
    show_safety(available, maximum, alloc)

    print("\n3. Новые запросы в этом состоянии")
    for pid, req in [(4, [3, 3, 0]), (0, [0, 2, 0]), (2, [1, 0, 0]), (3, [0, 1, 1])]:
        ok, reason, result = request_resources(pid, req, available, maximum, alloc)
        verdict = f"выдано, последовательность {names(result[2])}" if ok else f"отказ: {reason}"
        print(f"  P{pid} {tuple(req)}: {verdict}")

    print("\n4. Обнаружение взаимоблокировки (A=7, B=2, C=6)")
    d_alloc = [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]]
    d_request = [[0, 0, 0], [2, 0, 2], [0, 0, 0], [1, 0, 0], [0, 0, 2]]
    d_available = [0, 0, 0]
    print_table([("Allocation", d_alloc), ("Request", d_request)], len(d_alloc))
    print(f"  Available: {vec(d_available)}")
    blocked, seq = detect_deadlock(d_available, d_alloc, d_request)
    print(f"  заблокированы: {names(blocked) if blocked else 'нет'}, порядок завершения {names(seq)}")

    print("\n5. P2 запрашивает ещё 1 экземпляр C: Request[P2] = (0, 0, 1)")
    d_request[2] = [0, 0, 1]
    blocked, seq = detect_deadlock(d_available, d_alloc, d_request)
    print(f"  заблокированы: {names(blocked)}, могут завершиться: {names(seq)}")


if __name__ == "__main__":
    main()
