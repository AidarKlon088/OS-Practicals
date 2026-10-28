#!/usr/bin/env bash
# Запускает все алгоритмы на всех наборах и сохраняет вывод в results.txt,
# а результаты проверок — в test_results.txt.
cd "$(dirname "$0")"
{
  for f in set1.txt set2.txt set3.txt; do
    for a in fcfs sjf; do
      echo "\$ python3 sched.py --algo $a $f"
      python3 sched.py --algo "$a" "$f"
    done
    echo "\$ python3 sched.py --algo rr --quantum 3 $f"
    python3 sched.py --algo rr --quantum 3 "$f"
  done
  echo "\$ python3 sched.py --compare --quantum 3 set1.txt set2.txt set3.txt"
  python3 sched.py --compare --quantum 3 set1.txt set2.txt set3.txt
} > results.txt 2>&1
python3 test_sched.py > test_results.txt 2>&1
echo "Готово: results.txt, test_results.txt"
