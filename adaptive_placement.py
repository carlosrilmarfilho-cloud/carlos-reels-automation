from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RENDER = ROOT / "render.py"


def main() -> None:
    source = RENDER.read_text(encoding="utf-8")
    adaptive = (
        "safe_centers = tuple(dict.fromkeys((0.085, 0.13, 0.22, 0.32, 0.66, 0.76, 0.84) + "
        "tuple(step / 1000 for step in range(80, 841, 5))))"
    )

    if adaptive in source:
        print("Posicionamento adaptativo seguro já aplicado.")
        return

    pattern = r"(?m)^        safe_centers = .+$"
    matches = re.findall(pattern, source)
    if len(matches) != 1:
        raise RuntimeError("Não encontrei uma única geometria segura para ajustar a altura do texto")

    source = re.sub(pattern, "        " + adaptive, source, count=1)
    RENDER.write_text(source, encoding="utf-8")
    print(
        "Posicionamento adaptativo seguro aplicado: prioriza o topo livre e "
        "procura outras alturas entre 8% e 84%; os limites visuais e o bloqueio "
        "de sobreposição facial continuam inalterados."
    )


if __name__ == "__main__":
    main()
