#!/usr/bin/env python3
"""
PR8 — Проверки bankers.py на примерах, посчитанных вручную (см. README),
и на результатах из учебника Silberschatz.

Запуск:  python3 test_bankers.py
"""

from bankers import detect_deadlock, is_safe, need_matrix, request_resources

ALLOC = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
MAX = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
AVAILABLE = [3, 3, 2]

D_ALLOC = [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]]
D_REQUEST = [[0, 0, 0], [2, 0, 2], [0, 0, 0], [1, 0, 0], [0, 0, 2]]

passed = 0


def check(name, actual, expected):
    global passed
    assert actual == expected, f"{name}: ожидалось {expected}, получено {actual}"
    passed += 1
    print(f"OK  {name}: {actual}")


def main():
    check("Need", need_matrix(MAX, ALLOC),
          [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]])

    safe, seq, steps = is_safe(AVAILABLE, MAX, ALLOC)
    check("исходное состояние безопасно", safe, True)
    check("безопасная последовательность", seq, [1, 3, 4, 0, 2])
    check("Work в конце = всего ресурсов", steps[-1][1], [10, 5, 7])

    ok, _, (avail, alloc, seq) = request_resources(1, [1, 0, 2], AVAILABLE, MAX, ALLOC)
    check("P1 (1,0,2) выдано", ok, True)
    check("Available после P1", avail, [2, 3, 0])
    check("Allocation P1 после запроса", alloc[1], [3, 0, 2])
    check("последовательность после P1 (как в учебнике)", seq, [1, 3, 4, 0, 2])

    ok, reason, _ = request_resources(4, [3, 3, 0], avail, MAX, alloc)
    check("P4 (3,3,0): ресурсов нет", (ok, "недостаточно" in reason), (False, True))
    ok, reason, _ = request_resources(0, [0, 2, 0], avail, MAX, alloc)
    check("P0 (0,2,0): небезопасно", (ok, "небезопасным" in reason), (False, True))
    ok, reason, _ = request_resources(2, [7, 0, 0], AVAILABLE, MAX, ALLOC)
    check("P2 (7,0,0) > Need", (ok, "Need" in reason), (False, True))
    ok, _, _ = request_resources(3, [0, 0, 0], AVAILABLE, MAX, ALLOC)
    check("пустой запрос выдаётся", ok, True)

    safe, seq, _ = is_safe([0, 0, 0], MAX, ALLOC)
    check("Available = 0: небезопасно", (safe, seq), (False, []))
    safe, _, _ = is_safe([0, 0, 0], ALLOC, ALLOC)
    check("Need = 0 у всех: безопасно", safe, True)

    blocked, seq = detect_deadlock([0, 0, 0], D_ALLOC, D_REQUEST)
    check("обнаружение: блокировки нет", blocked, [])
    check("порядок завершения", seq, [0, 2, 3, 4, 1])

    request = [list(r) for r in D_REQUEST]
    request[2] = [0, 0, 1]
    blocked, seq = detect_deadlock([0, 0, 0], D_ALLOC, request)
    check("после запроса P2 (0,0,1): заблокированы", blocked, [1, 2, 3, 4])
    check("завершиться может только P0", seq, [0])

    print(f"\nПроверок пройдено: {passed}")


if __name__ == "__main__":
    main()
