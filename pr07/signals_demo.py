#!/usr/bin/env python3
"""
PR7 — Сигналы как способ межпроцессного взаимодействия.

1. Обработчики: потомок ловит SIGUSR1 (считает), SIGUSR2 (печатает отчёт) и
   SIGTERM (корректно завершается с кодом = числу полученных SIGUSR1).
   Родитель посылает сигналы через os.kill().
2. Обычные сигналы не накапливаются: потомок блокирует SIGUSR1
   (pthread_sigmask), родитель шлёт 5 штук, после разблокировки обработчик
   вызывается один раз.
3. SIGKILL нельзя перехватить: signal.signal(SIGKILL, ...) -> OSError;
   потомок, игнорирующий SIGTERM, завершается только по SIGKILL.

Для синхронизации («обработчики установлены») используется канал.

Запуск:  python3 signals_demo.py   (только Linux)
"""

import os
import signal
import time

SENT = 5


def log(msg):
    print(msg, flush=True)            # flush обязателен перед fork() и os._exit()


def wait_ready(fd):
    assert os.read(fd, 1) == b"!"
    os.close(fd)


def demo_handlers():
    log("1. Обработчики сигналов")
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r)
        got = {"usr1": 0}

        def on_usr1(signum, frame):
            got["usr1"] += 1

        def on_usr2(signum, frame):
            log(f"  [потомок {os.getpid()}] SIGUSR2: получено SIGUSR1 = {got['usr1']}")

        def on_term(signum, frame):
            log(f"  [потомок] SIGTERM: корректное завершение, код {got['usr1']}")
            os._exit(got["usr1"])

        signal.signal(signal.SIGUSR1, on_usr1)
        signal.signal(signal.SIGUSR2, on_usr2)
        signal.signal(signal.SIGTERM, on_term)
        os.write(w, b"!")
        os.close(w)
        while True:
            signal.pause()            # спим до прихода сигнала

    os.close(w)
    wait_ready(r)
    log(f"  родитель {os.getpid()} -> потомок {pid}: {SENT} x SIGUSR1 (пауза 0.05 с), SIGUSR2, SIGTERM")
    for _ in range(SENT):
        os.kill(pid, signal.SIGUSR1)
        time.sleep(0.05)
    os.kill(pid, signal.SIGUSR2)
    time.sleep(0.05)
    os.kill(pid, signal.SIGTERM)
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    log(f"  родитель: код завершения потомка = {code}")
    assert code == SENT
    log(f"  assert: потомок получил все {SENT} SIGUSR1 — OK\n")


def demo_coalescing():
    log("2. Заблокированные сигналы не накапливаются")
    ready_r, ready_w = os.pipe()
    sent_r, sent_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(ready_r)
        os.close(sent_w)
        got = [0]
        signal.signal(signal.SIGUSR1, lambda s, f: got.__setitem__(0, got[0] + 1))
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})
        os.write(ready_w, b"!")
        os.close(ready_w)
        wait_ready(sent_r)            # родитель отправил все сигналы
        pending = sorted(s.name for s in signal.sigpending())
        log(f"  [потомок] ожидающие (pending) сигналы: {pending}")
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGUSR1})
        time.sleep(0.05)
        log(f"  [потомок] после разблокировки обработчик вызван {got[0]} раз")
        os._exit(got[0])

    os.close(ready_w)
    os.close(sent_r)
    wait_ready(ready_r)
    for _ in range(SENT):
        os.kill(pid, signal.SIGUSR1)
    log(f"  родитель: отправил {SENT} x SIGUSR1, пока они заблокированы у потомка")
    os.write(sent_w, b"!")
    os.close(sent_w)
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    assert code == 1, f"ожидался 1 вызов обработчика, получено {code}"
    log(f"  assert: из {SENT} сигналов доставлен 1 — OK\n")


def demo_sigkill():
    log("3. SIGKILL нельзя перехватить")
    try:
        signal.signal(signal.SIGKILL, lambda s, f: None)
        raise AssertionError("обработчик SIGKILL установился")
    except OSError as e:
        log(f"  signal.signal(SIGKILL, ...) -> OSError: {e}")

    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.write(w, b"!")
        os.close(w)
        while True:
            signal.pause()

    os.close(w)
    wait_ready(r)
    os.kill(pid, signal.SIGTERM)
    time.sleep(0.2)
    done, _ = os.waitpid(pid, os.WNOHANG)
    log(f"  потомок {pid} игнорирует SIGTERM: через 0.2 с жив = {done == 0}")
    assert done == 0
    os.kill(pid, signal.SIGKILL)
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    log(f"  после SIGKILL: waitstatus_to_exitcode = {code} ({signal.Signals(-code).name})")
    assert code == -signal.SIGKILL
    log("  assert: процесс завершён сигналом SIGKILL — OK")


if __name__ == "__main__":
    demo_handlers()
    demo_coalescing()
    demo_sigkill()
