"""Рендеринг ASCII-баннеров через figlet-шрифты (официальная коллекция patorjk)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pyfiglet import Figlet

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
CONFIG_PATH = Path.home() / ".config" / "banner-gen" / "config.json"

_figlet_cache: dict[str, Figlet] = {}

DEFAULT_CONFIG = {
    "text": "my-app",
    "font": "Standard",
    "indent": 1,
    "last_path": "",
}


def list_fonts() -> list[str]:
    """Все доступные шрифты (имена файлов без расширения), без учёта регистра."""
    return sorted((f.stem for f in FONTS_DIR.glob("*.flf")), key=str.lower)


def resolve_font(name: str) -> str:
    """Точное имя шрифта или регистронезависимое совпадение; иначе ValueError."""
    fonts = list_fonts()
    if name in fonts:
        return name
    lowered = {f.lower(): f for f in fonts}
    if name.lower() in lowered:
        return lowered[name.lower()]
    raise ValueError(name)


def render(text: str, font: str, indent: int = 0) -> str:
    """Рендерит text шрифтом font; indent — отступ слева в пробелах."""
    fig = _figlet_cache.get(font)
    if fig is None:
        # pyfiglet подхватывает абсолюный путь без расширения и подставляет .flf
        fig = Figlet(font=str(FONTS_DIR / font))
        _figlet_cache[font] = fig
    art = str(fig.renderText(text))
    lines = [line.rstrip() for line in art.rstrip("\n").splitlines()]
    if indent > 0:
        pad = " " * indent
        lines = [pad + line if line.strip() else line for line in lines]
    return "\n".join(lines)


def copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def save(path: str, text: str) -> Path:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text + "\n", encoding="utf-8")
    return p


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
