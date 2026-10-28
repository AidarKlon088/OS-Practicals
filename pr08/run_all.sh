#!/usr/bin/env bash
# Запускает все программы PR8 и сохраняет вывод в results_*.txt
cd "$(dirname "$0")"
for prog in deadlock_demo.py dining_philosophers.py bankers.py test_bankers.py; do
  name=${prog%.py}
  { echo "\$ python3 $prog"; python3 "$prog"; } > "results_${name}.txt" 2>&1
  echo "== $prog (код возврата $?)"; cat "results_${name}.txt"; echo
done
