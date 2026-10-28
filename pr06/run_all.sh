#!/usr/bin/env bash
# Запускает все программы PR6 и сохраняет вывод в results_*.txt
cd "$(dirname "$0")"
for cmd in "race_demo.py" "lock_demo.py" "bank_demo.py" "bank_demo.py --unsafe" "producer_consumer.py"; do
  name=$(echo "$cmd" | sed 's/\.py//; s/ --/_/')
  { echo "\$ python3 $cmd"; python3 $cmd; } > "results_${name}.txt" 2>&1
  echo "== $cmd (код возврата $?)"; cat "results_${name}.txt"; echo
done
