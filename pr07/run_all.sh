#!/usr/bin/env bash
# Запускает все программы PR7 и сохраняет вывод в results_*.txt
cd "$(dirname "$0")"

for prog in pipe_demo.py shm_demo.py signals_demo.py; do
  name=${prog%.py}
  { echo "\$ python3 $prog"; python3 "$prog"; } > "results_${name}.txt" 2>&1
  echo "== $prog (код возврата $?)"; cat "results_${name}.txt"; echo
done

# FIFO: читатель и писатель — два независимых процесса (как в двух терминалах)
FIFO=/tmp/pr07.fifo
rm -f "$FIFO"
{
  echo "\$ python3 fifo_reader.py &   # терминал 1"
  python3 fifo_reader.py "$FIFO" &
  reader=$!
  sleep 1
  echo "\$ ls -l $FIFO"
  ls -l "$FIFO"
  echo "\$ python3 fifo_writer.py     # терминал 2"
  python3 fifo_writer.py "$FIFO"
  wait $reader
} > results_fifo.txt 2>&1
echo "== fifo (код возврата $?)"; cat results_fifo.txt; echo

# Каналы и FIFO средствами shell
SHELL_FIFO=/tmp/pr07_shell.fifo
{
  echo '$ ps -e | wc -l'
  ps -e | wc -l
  echo '$ ls -l /proc/self/fd | cat      # stdout ls — это канал'
  ls -l /proc/self/fd | cat
  echo "\$ mkfifo $SHELL_FIFO && ls -l $SHELL_FIFO"
  rm -f "$SHELL_FIFO"; mkfifo "$SHELL_FIFO" && ls -l "$SHELL_FIFO"
  echo "\$ echo 'привет через FIFO' > $SHELL_FIFO &  cat $SHELL_FIFO"
  echo 'привет через FIFO' > "$SHELL_FIFO" &
  cat "$SHELL_FIFO"
  wait
  rm -f "$SHELL_FIFO"
} > results_shell.txt 2>&1
echo "== shell"; cat results_shell.txt
