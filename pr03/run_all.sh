#!/usr/bin/env bash
# Запускает программы PR3 и сохраняет вывод в results_*.txt
cd "$(dirname "$0")"

# Процесс sleep: состояние, память, потоки, завершение через kill
{
  echo '$ sleep 100 &'
  sleep 100 &
  pid=$!
  sleep 0.3
  echo "\$ ps -o pid,ppid,stat,cmd -p $pid"
  ps -o pid,ppid,stat,cmd -p "$pid"
  echo "\$ grep -E 'State|VmRSS|Threads' /proc/$pid/status"
  grep -E 'State|VmRSS|Threads' "/proc/$pid/status"
  echo "\$ kill $pid"
  kill "$pid"
  wait "$pid"
  echo "код завершения: $? (128 + 15 = SIGTERM)"
} > results_sleep.txt 2>&1

{ echo '$ python3 fork_demo.py'; python3 fork_demo.py; } > results_fork.txt 2>&1

# Зомби: пока родитель спит 30 с, потомок уже завершён, но не «похоронен»
{
  echo '$ python3 zombie.py &'
  python3 zombie.py > /tmp/pr03_zombie.txt &
  sleep 1
  cat /tmp/pr03_zombie.txt
  parent=$(sed -n 's/Родитель PID=//p' /tmp/pr03_zombie.txt)
  child=$(sed -n 's/Дочерний PID=//p' /tmp/pr03_zombie.txt)
  echo "\$ ps -o pid,ppid,stat,cmd -p $parent,$child"
  ps -o pid,ppid,stat,cmd -p "$parent,$child"
  wait
  tail -1 /tmp/pr03_zombie.txt
  echo "\$ ps -o pid,stat -p $child      # после waitpid()"
  ps -o pid,stat -p "$child" || echo "(процесс $child больше не существует)"
  rm -f /tmp/pr03_zombie.txt
} > results_zombie.txt 2>&1

cat results_sleep.txt results_fork.txt results_zombie.txt
