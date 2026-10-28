#!/usr/bin/env python3
"""
Проверка sched.py на вручную посчитанных примерах.

Запуск:  python3 test_sched.py
Эталоны для set1 рассчитаны вручную (расчёт приведён в README).
Эталоны для set2 совпадают с классическим примером из учебника
Silberschatz «Operating System Concepts» (P1=24, P2=3, P3=3).
"""

import os
import tempfile

import sched as s

HERE = os.path.dirname(os.path.abspath(__file__))


def run(path, algo, quantum=3):
    gantt, rows, wt, tat = s.simulate(path, algo, quantum)
    finish = {r[0]: r[3] for r in rows}
    order = [g[0] for g in gantt]
    return order, finish, round(wt, 2), round(tat, 2)


def temp_set(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    f.write(text)
    f.close()
    return f.name


def check(name, actual, expected):
    assert actual == expected, f"{name}: получено {actual}, ожидалось {expected}"
    print(f"OK  {name}: {actual}")


set1 = os.path.join(HERE, "set1.txt")
set2 = os.path.join(HERE, "set2.txt")

# --- set1: ручной расчёт ---
order, finish, wt, tat = run(set1, "fcfs")
check("set1 FCFS порядок", order, ["P1", "P2", "P3", "P4"])
check("set1 FCFS WT/TAT", (wt, tat), (5.75, 11.25))

order, finish, wt, tat = run(set1, "sjf")
check("set1 SJF порядок", order, ["P1", "P2", "P4", "P3"])
check("set1 SJF WT/TAT", (wt, tat), (5.25, 10.75))

order, finish, wt, tat = run(set1, "rr", 3)
check("set1 RR q=3 порядок", order, ["P1", "P2", "P3", "P4", "P1", "P3", "P4", "P3"])
check("set1 RR q=3 завершение", finish, {"P1": 14, "P2": 6, "P3": 22, "P4": 20})
check("set1 RR q=3 WT/TAT", (wt, tat), (8.5, 14.0))

# --- set2: пример из учебника ---
check("set2 FCFS WT", run(set2, "fcfs")[2], 17.0)
check("set2 SJF WT", run(set2, "sjf")[2], 3.0)
check("set2 RR q=4 WT (учебник: 5.66)", run(set2, "rr", 4)[2], 5.67)

# --- правило RR: новый процесс встаёт в очередь раньше вытесненного ---
path = temp_set("A 0 4 1\nB 2 2 1\n")
check("RR новый раньше вытесненного", run(path, "rr", 2)[0], ["A", "B", "A"])
os.remove(path)

# --- равенство burst в SJF: побеждает меньший arrival, затем порядок файла ---
path = temp_set("A 0 1 1\nC 1 3 1\nB 0 3 1\n")
check("SJF равный burst", run(path, "sjf")[0], ["A", "B", "C"])
os.remove(path)

# --- простой CPU ---
path = temp_set("A 0 2 1\nB 5 1 1\n")
for algo in ("fcfs", "sjf", "rr"):
    check(f"простой CPU ({algo})", run(path, algo)[0], ["A", "idle", "B"])
os.remove(path)

print("\nВсе проверки пройдены.")
