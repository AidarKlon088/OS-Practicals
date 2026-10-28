#!/usr/bin/env python3
"""
PR8 — Обедающие философы.

5 философов, между соседями по одной вилке (блокировке). Чтобы есть, философу
нужны обе соседние вилки. Сравниваются три стратегии:

  naive   — каждый берёт левую, затем правую. Barrier после левой вилки
            гарантирует, что все взяли по одной -> взаимоблокировка (цикл
            P0 -> P1 -> ... -> P4 -> P0 в графе ожидания).
  ordered — сначала вилка с меньшим номером: философ P4 берёт F0, затем F4.
            Порядок ресурсов глобальный — циклического ожидания нет.
  waiter  — «официант» (Semaphore(N-1)) пускает к столу не более 4 философов,
            поэтому хотя бы один всегда может взять обе вилки.

Для рабочих стратегий проверяется: каждый поел MEALS раз, соседи никогда не
ели одновременно, одновременно ели не более N // 2 философов.

Запуск:  python3 dining_philosophers.py [--strategy all|naive|ordered|waiter]
"""

import argparse
import random
import threading
import time

from deadlock_demo import TrackedLock, find_cycle, format_cycle

N = 5
MEALS = 100
EAT = 0.001
THINK = 0.001


def run(strategy):
    forks = [TrackedLock(f"F{i}") for i in range(N)]
    waiter = threading.Semaphore(N - 1)
    barrier = threading.Barrier(N) if strategy == "naive" else None
    meals = [0] * N
    wait_time = [0.0] * N
    eating = [False] * N
    stats = {"max_eating": 0, "violations": 0}
    guard = threading.Lock()

    def philosopher(i):
        left, right = forks[i], forks[(i + 1) % N]
        if strategy == "ordered":
            first, second = sorted((left, right), key=lambda f: int(f.name[1:]))
        else:
            first, second = left, right
        rnd = random.Random(i)
        for m in range(MEALS):
            time.sleep(rnd.uniform(0, THINK))          # думает
            start = time.perf_counter()
            if strategy == "waiter":
                waiter.acquire()
            first.acquire()
            if barrier is not None and m == 0:
                barrier.wait()                         # все держат левую вилку
            second.acquire()
            wait_time[i] += time.perf_counter() - start
            with guard:
                if eating[(i - 1) % N] or eating[(i + 1) % N]:
                    stats["violations"] += 1
                eating[i] = True
                stats["max_eating"] = max(stats["max_eating"], sum(eating))
            time.sleep(EAT)                            # ест
            with guard:
                eating[i] = False
            meals[i] += 1
            second.release()
            first.release()
            if strategy == "waiter":
                waiter.release()

    threads = [threading.Thread(target=philosopher, args=(i,), name=f"P{i}", daemon=True)
               for i in range(N)]
    start = time.perf_counter()
    for t in threads:
        t.start()

    if strategy == "naive":
        cycle, deadline = None, time.monotonic() + 2
        while cycle is None and time.monotonic() < deadline:
            time.sleep(0.1)
            cycle = find_cycle()
        alive = sum(t.is_alive() for t in threads)
        print(f"  через 2 с: живых потоков {alive} из {N}, съедено обедов {sum(meals)}")
        print("  вилки заняты: " + ", ".join(f"{f.name}={f.owner.name}" for f in forks if f.owner))
        assert cycle is not None and len(cycle) == N, "цикл из 5 философов не найден"
        print(f"  граф ожидания: {format_cycle(cycle)}")
        print("  assert: все 5 философов ждут друг друга по кругу — взаимоблокировка — OK\n")
        return

    for t in threads:
        t.join(timeout=60)
    elapsed = time.perf_counter() - start
    assert not any(t.is_alive() for t in threads), "философы зависли"
    print(f"  время: {elapsed:.3f} с, обедов: {meals}")
    print("  ожидание вилок, с: " + " ".join(f"P{i}={w:.3f}" for i, w in enumerate(wait_time)))
    print(f"  максимум едят одновременно: {stats['max_eating']}, "
          f"соседи ели одновременно: {stats['violations']} раз")
    assert meals == [MEALS] * N
    assert stats["violations"] == 0
    assert stats["max_eating"] <= N // 2
    print(f"  assert: все поели по {MEALS} раз, вилки не делились — OK\n")


TITLES = {
    "naive": "левая, затем правая вилка (наивно)",
    "ordered": "сначала вилка с меньшим номером",
    "waiter": f"официант: не более {N - 1} за столом",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=["all", *TITLES], default="all")
    choice = parser.parse_args().strategy
    print(f"Философов: {N}, обедов у каждого: {MEALS}\n")
    for strategy, title in TITLES.items():
        if choice in ("all", strategy):
            print(f"Стратегия {strategy}: {title}")
            run(strategy)


if __name__ == "__main__":
    main()
