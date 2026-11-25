"""CLI-режим banner-gen. Без аргументов запускает TUI."""
from __future__ import annotations

import argparse
import sys

from . import engine

EPILOG = """\
примеры:
  banner-gen                                запустить TUI (живое превью шрифтов)
  banner-gen 'my-app'                       показать арт шрифтом Standard
  banner-gen 'my-app' -f 'ANSI Shadow' --indent 1
  banner-gen 'my-app' -f Standard --indent 1 \\
      -o src/main/resources/banner.txt
  banner-gen 'my-app' -f Slant --copy
  banner-gen --search slant                 найти шрифт по подстроке
  banner-gen --list                         все доступные шрифты

имена шрифтов с пробелами берутся в кавычки; регистр не важен
(shadow = Shadow = sHaDoW).

настройки TUI хранятся в ~/.config/banner-gen/config.json
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="banner-gen",
        description=(
            "Генератор ASCII-баннеров для Spring Boot (banner.txt). "
            "Офлайн, 335 официальных figlet-шрифтов patorjk. "
            "Без аргументов запускает TUI."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", metavar="ТЕКСТ",
                        help="текст баннера (без него запускается TUI)")
    parser.add_argument("-f", "--font", default="Standard", metavar="ШРИФТ",
                        help="шрифт из banner-gen --list (по умолчанию: Standard)")
    parser.add_argument("-o", "--out", metavar="ПУТЬ",
                        help="записать результат в файл, напр. .../banner.txt")
    parser.add_argument("--copy", action="store_true",
                        help="скопировать ASCII-арт в буфер обмена (pbcopy)")
    parser.add_argument("--indent", type=int, default=0, metavar="N",
                        help="отступ слева в пробелах (для классического вида: 1)")
    parser.add_argument("-l", "--list", action="store_true", dest="list_fonts",
                        help="показать список всех шрифтов и выйти")
    parser.add_argument("--search", metavar="ШАБЛОН",
                        help="найти шрифты по подстроке и выйти")
    args = parser.parse_args(argv)

    if args.list_fonts or args.search:
        fonts = engine.list_fonts()
        if args.search:
            fonts = [f for f in fonts if args.search.lower() in f.lower()]
        print("\n".join(fonts) or "Ничего не найдено")
        return 0

    if not args.text:
        from .app import BannerApp

        BannerApp().run()
        return 0

    try:
        font = engine.resolve_font(args.font)
    except ValueError:
        matches = [f for f in engine.list_fonts() if args.font.lower() in f.lower()]
        print(f"Шрифт не найден: {args.font}", file=sys.stderr)
        if matches:
            print("Возможно, вы имели в виду: " + ", ".join(matches[:10]),
                  file=sys.stderr)
        return 1

    try:
        art = engine.render(args.text, font, args.indent)
    except Exception as exc:  # noqa: BLE001
        print(f"Не удалось отрендерить: {exc}", file=sys.stderr)
        return 1

    if args.out:
        saved = engine.save(args.out, art)
        print(f"Сохранено: {saved}", file=sys.stderr)
    if args.copy:
        engine.copy_to_clipboard(art)
        print("Скопировано в буфер обмена", file=sys.stderr)
    if not args.out:
        print(art)
    return 0


if __name__ == "__main__":
    sys.exit(main())
