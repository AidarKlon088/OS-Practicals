#!/usr/bin/env python3
"""
PR8 — Взаимоблокировка двух потоков и способы её избежать.

1. deadlock — поток T1 берёт A, затем B; поток T2 — B, затем A. Barrier
   гарантирует, что оба успеют взять первую блокировку -> взаимоблокировка.
   Сторожевой код строит граф ожидания (wait-for) и находит в нём цикл,
   а состояние потоков читается из /proc/self/task/TID.
2. ordered — обе блокировки всегда берутся в одном порядке (A, затем B).
   Условие «циклическое ожидание» нарушено — взаимоблокировки нет.
3. timeout — вторая блокировка берётся с acquire(timeout=...); при неудаче поток
   отдаёт первую (откат) и повторяет попытку после случайной паузы.

Запуск:  python3 deadlock_demo.py [--mode all|deadlock|ordered|timeout]
"""

import argparse
import random
import threading
import time

ITER = 10_000
state_lock = threading.Lock()
waiting = {}                      # поток -> TrackedLock, которую он ждёт


class TrackedLock:
    """Обёртка над threading.Lock: помнит владельца и ожидающих (для графа ожидания)."""

    def __init__(self, name):
        self.name = name
        self._lock = threading.Lock()
        self.owner = None

    def acquire(self, timeout=-1):
        me = threading.current_thread()
        with state_lock:
            waiting[me] = self
        ok = self._lock.acquire(timeout=timeout)
        with state_lock:
            del waiting[me]
            if ok:
                self.owner = me
        return ok

    def release(self):
        with state_lock:
            self.owner = None
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


def find_cycle():
    """Ищет цикл: поток -(ждёт блокировку)-> её владелец -> ...
    Возвращает список (поток, блокировка, владелец) или None."""
    with state_lock:
        edges = {t: (lock.name, lock.owner) for t, lock in waiting.items() if lock.owner}
    for start in edges:
        path, seen, t = [], set(), start
        while t in edges and t not in seen:
            seen.add(t)
            lock_name, owner = edges[t]
            path.append((t, lock_name, owner))
            t = owner
        if t is start:
            return path
    return None


def format_cycle(cycle):
    text = cycle[0][0].name
    for _, lock_name, owner in cycle:
        text += f" --ждёт {lock_name}--> {owner.name}"
    return text


def thread_state(tid):
    """Состояние потока из /proc: R — работает, S — спит (ждёт)."""
    try:
        with open(f"/proc/self/task/{tid}/stat") as f:
            state = f.read().rsplit(")", 1)[1].split()[0]
        with open(f"/proc/self/task/{tid}/wchan") as f:
            wchan = f.read().strip() or "-"
    except OSError:
        return "?", "?"
    return state, wchan


def demo_deadlock():
    print("1. Взаимоблокировка: T1 берёт A -> B, T2 берёт B -> A")
    a, b = TrackedLock("A"), TrackedLock("B")
    barrier = threading.Barrier(2)
    tids = {}

    def worker(first, second):
        me = threading.current_thread().name
        tids[me] = threading.get_native_id()
        with first:
            print(f"  {me}: захватил {first.name}, хочу {second.name}", flush=True)
            barrier.wait()            # оба держат свою первую блокировку
            with second:
                print(f"  {me}: захватил обе (сюда не дойдём)", flush=True)

    threads = [threading.Thread(target=worker, args=(a, b), name="T1", daemon=True),
               threading.Thread(target=worker, args=(b, a), name="T2", daemon=True)]
    for t in threads:
        t.start()

    cycle, deadline = None, time.monotonic() + 2
    while cycle is None and time.monotonic() < deadline:
        time.sleep(0.1)
        cycle = find_cycle()
    for t in threads:
        t.join(timeout=1)
    print(f"  через 2 с: T1 жив = {threads[0].is_alive()}, T2 жив = {threads[1].is_alive()}")
    for name, tid in sorted(tids.items()):
        state, wchan = thread_state(tid)
        print(f"  {name} (TID {tid}): состояние {state}, wchan = {wchan}")
    assert cycle is not None, "цикл в графе ожидания не найден"
    assert all(t.is_alive() for t in threads)
    print(f"  граф ожидания: {format_cycle(cycle)}")
    print("  assert: найден цикл ожидания — взаимоблокировка — OK\n")


def run_pair(worker):
    a, b = TrackedLock("A"), TrackedLock("B")
    shared = {"n": 0}
    threads = [threading.Thread(target=worker, args=(a, b, shared), name="T1", daemon=True),
               threading.Thread(target=worker, args=(b, a, shared), name="T2", daemon=True)]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.perf_counter() - start
    assert not any(t.is_alive() for t in threads), "потоки зависли"
    return shared["n"], elapsed


def demo_ordered():
    print(f"2. Единый порядок захвата: 2 потока x {ITER} операций с обеими блокировками")

    def worker(first, second, shared):
        lo, hi = sorted((first, second), key=lambda lock: lock.name)   # всегда A, затем B
        for _ in range(ITER):
            with lo:
                with hi:
                    shared["n"] += 1

    n, elapsed = run_pair(worker)
    print(f"  выполнено операций: {n} из {2 * ITER}, время {elapsed:.3f} с")
    assert n == 2 * ITER
    print("  assert: все операции выполнены, взаимоблокировки нет — OK\n")


def demo_timeout():
    print(f"3. Захват с таймаутом и откатом: 2 потока x {ITER} операций, порядок A->B и B->A")
    retries = {}
    barrier = threading.Barrier(2)

    def worker(first, second, shared):
        me = threading.current_thread().name
        rnd = random.Random(me)
        retries[me] = 0
        provoke = True                # первая попытка: гарантированный конфликт
        for _ in range(ITER):
            while True:
                first.acquire()
                if provoke:
                    barrier.wait()
                    provoke = False
                if second.acquire(timeout=0.01):
                    shared["n"] += 1
                    second.release()
                    first.release()
                    break
                first.release()       # откат: отдаём то, что держим
                retries[me] += 1
                time.sleep(rnd.uniform(0, 0.005))

    n, elapsed = run_pair(worker)
    print(f"  выполнено операций: {n} из {2 * ITER}, время {elapsed:.3f} с")
    print(f"  откатов (таймаут на второй блокировке): T1 = {retries['T1']}, T2 = {retries['T2']}")
    assert n == 2 * ITER
    assert retries["T1"] + retries["T2"] > 0
    print("  assert: конфликты были, но разрешились откатом — OK\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "deadlock", "ordered", "timeout"], default="all")
    mode = parser.parse_args().mode
    if mode in ("all", "deadlock"):
        demo_deadlock()
    if mode in ("all", "ordered"):
        demo_ordered()
    if mode in ("all", "timeout"):
        demo_timeout()
    if mode in ("all", "deadlock"):
        print("Заблокированные daemon-потоки T1/T2 из п.1 завершатся вместе с процессом.")


if __name__ == "__main__":
    main()
