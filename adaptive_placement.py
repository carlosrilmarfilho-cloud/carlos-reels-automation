from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
RENDER = ROOT / "render.py"


def main() -> None:
    source = RENDER.read_text(encoding="utf-8")
    fixed = "safe_centers = (0.22, 0.32, 0.66, 0.76)"
    adaptive = (
        "safe_centers = tuple(dict.fromkeys((0.22, 0.32, 0.66, 0.76) + "
        "tuple(step / 1000 for step in range(160, 811, 5))))"
    )

    if adaptive in source:
        print("Posicionamento adaptativo já aplicado.")
        return
    if fixed not in source:
        raise RuntimeError("Geometria autoral esperada não encontrada; não vou alterar o gate às cegas")

    source = source.replace(fixed, adaptive, 1)
    RENDER.write_text(source, encoding="utf-8")
    print(
        "Posicionamento adaptativo aplicado: mantém 22% como primeira opção e "
        "procura outras alturas entre 16% e 81% somente quando necessário; "
        "o bloqueio de sobreposição facial continua inalterado."
    )


if __name__ == "__main__":
    main()
