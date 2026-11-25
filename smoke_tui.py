"""Смоук-тест TUI без терминала (Textual pilot). Запуск: .venv/bin/python3 smoke_tui.py"""
import asyncio
import pathlib
import tempfile

from banner_gen import engine
from banner_gen.app import BannerApp

# конфиг теста — во временную директорию, не трогаем пользовательский
engine.CONFIG_PATH = pathlib.Path(tempfile.gettempdir()) / "banner-gen-smoke-config.json"
if engine.CONFIG_PATH.exists():
    engine.CONFIG_PATH.unlink()  # старт всегда с дефолтов


async def run_checks() -> None:
    app = BannerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # шрифты загрузились
        assert len(app.all_fonts) > 300, len(app.all_fonts)
        await pilot.pause()

        # стартовое превью отрендерилось
        assert app.art

        # справка открывается и закрывается
        await pilot.press("f1")
        await pilot.pause()
        assert len(app.screen_stack) == 2, len(app.screen_stack)
        await pilot.press("f1")
        await pilot.pause()
        assert len(app.screen_stack) == 1, len(app.screen_stack)

        # набираем текст — превью обновилось
        before = app.art
        text_input = app.query_one("#text-input")
        text_input.value = "Test Banner"
        await pilot.pause()
        assert app.art and app.art != before

        # поиск сужает список и выбирается шрифт
        search = app.query_one("#font-search")
        search.value = "slant"
        await pilot.pause()
        assert app.visible_fonts and all("slant" in f.lower() for f in app.visible_fonts)
        option_list = app.query_one("#font-list")
        option_list.highlighted = app.visible_fonts.index("Slant")
        await pilot.pause()
        assert app.current_font == "Slant", app.current_font

        # сброс поиска
        search.value = ""
        await pilot.pause()
        assert len(app.visible_fonts) == len(app.all_fonts)

        # выделение другого шрифта из списка
        option_list.highlighted = app.visible_fonts.index("ANSI Shadow")
        await pilot.pause()
        assert app.current_font == "ANSI Shadow", app.current_font
        assert any(c in app.art for c in "█▄▀"), app.art[:80]

        # отступ
        indent = app.query_one("#indent-input")
        indent.value = "3"
        await pilot.pause()
        assert app.art.splitlines()[0].startswith("   "), repr(app.art[:10])

        # сохранение через диалог (Ctrl+S → путь → Enter)
        out = pathlib.Path(tempfile.gettempdir()) / "banner-gen-smoke-banner.txt"
        if out.exists():
            out.unlink()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert len(app.screen_stack) == 2, "диалог сохранения не открылся"
        path_input = app.screen.query_one("#dlg-path")
        path_input.value = str(out)
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.screen_stack) == 1, "диалог не закрылся"
        assert out.exists(), "файл не создан"
        assert out.read_text().startswith("   ")
        out.unlink()

    print("TUI SMOKE OK:", len(app.all_fonts), "шрифтов")


asyncio.run(run_checks())
