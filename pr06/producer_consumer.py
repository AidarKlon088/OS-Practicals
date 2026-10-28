#!/usr/bin/env python3
"""
PR6 — Производитель–потребитель через ограниченную очередь queue.Queue(maxsize=3).

Производитель быстрый (новый элемент каждые 0.01 с), потребитель медленный
(обрабатывает элемент 0.05 с). Очередь быстро заполняется, и q.put() блокирует
производителя, пока потребитель не заберёт элемент.

В конце проверяется:
  * потребитель получил все элементы, в том же порядке;
  * размер очереди ни разу не превысил maxsize;
  * производитель действительно ждал на заполненной очереди.

Запуск:  python3 producer_consumer.py
"""

import queue
import threading
import time

MAXSIZE = 3
ITEMS = 10
PRODUCE_DELAY = 0.01
CONSUME_DELAY = 0.05
STOP = None                       # «ядовитая пилюля» — сигнал окончания

q = queue.Queue(maxsize=MAXSIZE)
produced, consumed = [], []
max_seen = 0
waits = []                        # сколько производитель ждал на каждом put
print_lock = threading.Lock()
t0 = time.perf_counter()


def log(msg):
    with print_lock:
        print(f"[{time.perf_counter() - t0:6.3f} с] {msg}")


def producer():
    global max_seen
    for i in range(1, ITEMS + 1):
        time.sleep(PRODUCE_DELAY)
        item = f"item-{i}"
        if q.full():
            log(f"производитель: очередь полна ({q.qsize()}/{MAXSIZE}), ждёт для {item}")
        start = time.perf_counter()
        q.put(item)               # блокируется, пока в очереди нет места
        waited = time.perf_counter() - start
        waits.append(waited)
        produced.append(item)
        max_seen = max(max_seen, q.qsize())
        log(f"производитель: положил {item} (ждал {waited:.3f} с), в очереди {q.qsize()}")
    q.put(STOP)
    log("производитель: закончил")


def consumer():
    while True:
        item = q.get()            # блокируется, если очередь пуста
        if item is STOP:
            q.task_done()
            break
        time.sleep(CONSUME_DELAY)  # «обработка»
        consumed.append(item)
        log(f"    потребитель: обработал {item}")
        q.task_done()
    log("    потребитель: закончил")


def main():
    threads = [threading.Thread(target=producer), threading.Thread(target=consumer)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    blocked = sum(1 for w in waits if w > PRODUCE_DELAY / 2)
    print()
    print(f"Произведено: {len(produced)}, потреблено: {len(consumed)}")
    print(f"Максимальный размер очереди: {max_seen} (maxsize = {MAXSIZE})")
    print(f"put() блокировался {blocked} раз(а), суммарное ожидание {sum(waits):.3f} с")

    assert consumed == produced, "потеряны или переставлены элементы!"
    assert max_seen <= MAXSIZE, "очередь превысила maxsize!"
    assert blocked > 0, "производитель ни разу не ждал — очередь не заполнялась"
    assert q.empty()
    print("assert: все элементы получены по порядку, очередь не переполнялась — OK")


if __name__ == "__main__":
    main()
