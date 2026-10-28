#!/usr/bin/env bash

total=0
max_errors=-1
max_file=""

for f in data/*.log; do
    [ -f "$f" ] || continue

    count=$(grep -c "ERROR" "$f" || true)

    echo "$f: $count ошибок"

    total=$((total + count))

    if (( count > max_errors )); then
        max_errors=$count
        max_file=$f
    fi
done

echo "-----------------------------"
echo "Всего ошибок: $total"
echo "Больше всего ошибок: $max_file"
echo "Количество ошибок: $max_errors"