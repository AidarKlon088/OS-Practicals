#!/usr/bin/env python3
"""
PR4 — сравнение последовательной и 4-поточной загрузки 20 файлов
через ЛОКАЛЬНЫЙ HTTP-сервер (в интернет ничего не отправляется).

Что делает программа:
  1. Создаёт во временном каталоге 20 файлов по 256 КБ.
  2. Запускает HTTP-сервер на 127.0.0.1 (порт выбирает ОС) в фоновом потоке.
  3. Скачивает все 20 файлов: сначала последовательно, затем 4 потоками
     (ThreadPoolExecutor(max_workers=4)), и измеряет время.
  4. Повторяет измерение для двух сценариев:
       delay=0     - чистый localhost, задержки сети почти нет;
       delay=0.1   - сервер «спит» 0.1 с перед ответом, имитируя
                     задержку реальной сети (I/O-ожидание).
  5. Проверяет, что скачанные данные совпадают с исходными.

Запуск:
  python3 download_demo.py
"""

import concurrent.futures
import http.server
import os
import tempfile
import threading
import time
import urllib.request

NUM_FILES = 20
FILE_SIZE = 256 * 1024   # 256 КБ
WORKERS = 4
REPEATS = 3              # каждое измерение повторяем 3 раза


def make_handler(directory, delay):
    """Создаёт класс обработчика, который раздаёт файлы из directory."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def do_GET(self):
            if delay:
                time.sleep(delay)   # имитация сетевой задержки
            super().do_GET()

        def log_message(self, *args):
            pass                    # не засоряем вывод логами сервера

    return Handler


def download(url):
    """Скачать один файл и вернуть его байты."""
    with urllib.request.urlopen(url) as response:
        return response.read()


def sequential(urls):
    return [download(u) for u in urls]


def threaded(urls):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(download, urls))


def measure(func, urls, originals):
    """Возвращает время работы func(urls) и проверяет содержимое файлов."""
    start = time.perf_counter()
    data = func(urls)
    elapsed = time.perf_counter() - start
    assert data == originals, "скачанные данные не совпадают с исходными!"
    return elapsed


def main():
    print(f"Ядер CPU (os.cpu_count): {os.cpu_count()}")
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Готовим 20 файлов со случайным содержимым
        originals = []
        for i in range(NUM_FILES):
            content = os.urandom(FILE_SIZE)
            with open(os.path.join(tmp, f"file{i:02}.bin"), "wb") as f:
                f.write(content)
            originals.append(content)

        for delay in (0, 0.1):
            # 2. Многопоточный сервер, чтобы он сам не был узким местом
            server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), make_handler(tmp, delay))
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            urls = [f"http://127.0.0.1:{port}/file{i:02}.bin"
                    for i in range(NUM_FILES)]

            print(f"\nСценарий: задержка сервера = {delay} с, "
                  f"{NUM_FILES} файлов x {FILE_SIZE // 1024} КБ")
            seq_times, thr_times = [], []
            for r in range(1, REPEATS + 1):
                t_seq = measure(sequential, urls, originals)
                t_thr = measure(threaded, urls, originals)
                seq_times.append(t_seq)
                thr_times.append(t_thr)
                print(f"  попытка {r}: последовательно = {t_seq:.3f} с, "
                      f"{WORKERS} потока = {t_thr:.3f} с")
            avg_seq = sum(seq_times) / REPEATS
            avg_thr = sum(thr_times) / REPEATS
            print(f"  среднее: последовательно = {avg_seq:.3f} с, "
                  f"{WORKERS} потока = {avg_thr:.3f} с, "
                  f"ускорение = {avg_seq / avg_thr:.2f}x")
            server.shutdown()
            server.server_close()
    print("\nПроверка содержимого: все файлы скачаны без искажений.")


if __name__ == "__main__":
    main()
