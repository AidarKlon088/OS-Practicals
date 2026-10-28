#!/usr/bin/env python3
"""
PR6 — Безопасные переводы между двумя счетами.

Два счёта A и B (по 1000). Четыре потока делают по 10 000 случайных переводов
в обе стороны (A->B и B->A). Отдельный поток-аудитор во время работы
проверяет, что сумма денег не меняется.

У каждого счёта своя блокировка. Перевод захватывает ОБЕ блокировки
всегда в одном порядке (по номеру счёта) — так не возникает взаимоблокировки
(подробнее — PR8).

Режимы:
  python3 bank_demo.py            # безопасный режим (с блокировками)
  python3 bank_demo.py --unsafe   # без блокировок — видно, что сумма ломается
"""

import argparse
import random
import threading
import time

INITIAL = 1000
THREADS = 4
TRANSFERS = 10_000


class Account:
    def __init__(self, number, balance):
        self.number = number          # номер счёта задаёт порядок захвата блокировок
        self.balance = balance
        self.lock = threading.Lock()


def transfer_safe(src, dst, amount):
    """Перевод с блокировками. Возвращает True, если денег хватило."""
    first, second = sorted((src, dst), key=lambda a: a.number)
    with first.lock:
        with second.lock:
            if src.balance < amount:
                return False
            balance = src.balance
            time.sleep(0)             # переключение внутри критической секции не опасно
            src.balance = balance - amount
            dst.balance += amount
            return True


def transfer_unsafe(src, dst, amount):
    """Тот же перевод без блокировок — демонстрация ошибки."""
    if src.balance < amount:
        return False
    balance = src.balance
    time.sleep(0)                     # другой поток успевает изменить баланс
    src.balance = balance - amount
    dst.balance += amount
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--unsafe", action="store_true", help="без блокировок")
    args = parser.parse_args()
    transfer = transfer_unsafe if args.unsafe else transfer_safe

    a, b = Account(1, INITIAL), Account(2, INITIAL)
    total = a.balance + b.balance
    done = threading.Event()
    audit = {"checks": 0, "errors": 0}
    stats = {"ok": 0, "rejected": 0}
    stats_lock = threading.Lock()

    def client(seed):
        rnd = random.Random(seed)       # свой генератор у каждого потока
        ok = rejected = 0
        for _ in range(TRANSFERS):
            src, dst = (a, b) if rnd.random() < 0.5 else (b, a)
            if transfer(src, dst, rnd.randint(1, 200)):
                ok += 1
            else:
                rejected += 1
        with stats_lock:
            stats["ok"] += ok
            stats["rejected"] += rejected

    def auditor():
        """Во время работы проверяет сумму, захватив обе блокировки по порядку."""
        while not done.is_set():
            if args.unsafe:
                current = a.balance + b.balance
            else:
                with a.lock, b.lock:
                    current = a.balance + b.balance
            audit["checks"] += 1
            if current != total:
                audit["errors"] += 1
            time.sleep(0.001)

    mode = "БЕЗ блокировок" if args.unsafe else "с блокировками"
    print(f"Режим: {mode}. Начальные балансы: A={a.balance}, B={b.balance}, сумма={total}")
    audit_thread = threading.Thread(target=auditor)
    audit_thread.start()
    clients = [threading.Thread(target=client, args=(i,)) for i in range(THREADS)]
    start = time.perf_counter()
    for t in clients:
        t.start()
    for t in clients:
        t.join()
    elapsed = time.perf_counter() - start
    done.set()
    audit_thread.join()

    final = a.balance + b.balance
    print(f"Переводов выполнено: {stats['ok']}, отклонено (мало денег): {stats['rejected']}")
    print(f"Итоговые балансы: A={a.balance}, B={b.balance}, сумма={final}")
    print(f"Проверок аудитора во время работы: {audit['checks']}, нарушений суммы: {audit['errors']}")
    print(f"Время: {elapsed:.3f} с")

    if args.unsafe:
        print("Сумма сохранилась" if final == total else
              f"ОШИБКА: сумма изменилась на {final - total} (гонка данных)")
    else:
        assert final == total, "общая сумма изменилась!"
        assert a.balance >= 0 and b.balance >= 0, "отрицательный баланс!"
        assert audit["errors"] == 0, "аудитор видел неверную сумму!"
        assert stats["ok"] + stats["rejected"] == THREADS * TRANSFERS
        print("assert: общая сумма сохранена, балансы неотрицательны — OK")


if __name__ == "__main__":
    main()
