from pathlib import Path

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

for i in range(1, 51):
    lines = []

    for j in range(1, 21):
        level = "ERROR" if j % (i % 7 + 2) == 0 else "INFO"

        lines.append(
            f"2026-10-27 10:{j:02d}:00 "
            f"{level} module=system msg=event_{j}"
        )

    file_path = data_dir / f"{i:02d}.log"
    file_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

print("Создано 50 файлов журналов.")