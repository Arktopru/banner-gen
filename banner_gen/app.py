"""TUI-генератор ASCII-баннеров для Spring Boot (banner.txt)."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option
from rich.text import Text

from . import engine

WIDTH_HINT = 80

HELP_TEXT = """banner-gen — ASCII-баннеры для Spring Boot (banner.txt)

Работа
  1. Введите текст баннера сверху — превью обновится сразу
  2. Ищите шрифт в поле «поиск…» слева, листайте стрелками ↑/↓
  3. Поле «отступ» — пробелы слева (классический вид: 1)
  4. Сохраните (Ctrl+S) или скопируйте (Ctrl+C)

Клавиши
  Ctrl+C   скопировать ASCII-арт в буфер обмена
  Ctrl+S   сохранить в файл (диалог пути, путь запоминается)
  Ctrl+Q   выход
  F1       эта справка

Примечания
  • В статусной строке — размеры арта; если шире 80 колонок,
    в консоли он может перенестись
  • Последние текст, шрифт, отступ и путь сохраняются в
    ~/.config/banner-gen/config.json
  • CLI: banner-gen --help
"""


class HelpScreen(ModalScreen[None]):
    """Справка по клавишам и работе (F1)."""

    CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Vertical {
        width: 78; height: auto; max-height: 90%;
        border: round $primary; padding: 1 2;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("f1", "close", priority=True),
        Binding("escape", "close", priority=True),
        Binding("enter", "close", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(Text(HELP_TEXT))

    def action_close(self) -> None:
        self.dismiss(None)


class SaveDialog(ModalScreen[str | None]):
    """Диалог сохранения banner.txt."""

    CSS = """
    SaveDialog { align: center middle; }
    SaveDialog > Vertical {
        width: 84; height: auto;
        border: round $primary; padding: 1 2;
        background: $surface;
    }
    #dlg-hint { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", priority=True)]

    def __init__(self, default_path: str):
        super().__init__()
        self.default_path = default_path

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Сохранить banner.txt в:", id="dlg-title")
            yield Input(value=self.default_path, id="dlg-path")
            yield Static("Enter — сохранить · Esc — отмена", id="dlg-hint")

    def on_mount(self) -> None:
        inp = self.query_one("#dlg-path", Input)
        inp.focus()
        inp.cursor_position = len(inp.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class BannerApp(App):
    """Живое превью: список шрифтов + результат, сохранение и копирование."""

    CSS = """
    #text-row { height: 3; dock: top; }
    #text-input { width: 1fr; }
    #indent-input { width: 12; }
    #body { height: 1fr; }
    #font-col { width: 34; height: 100%; }
    #font-search { height: 3; }
    #font-list { height: 1fr; }
    #preview {
        width: 1fr; height: 1fr;
        overflow-x: auto; overflow-y: auto;
        padding: 1 2;
    }
    #status { dock: bottom; height: 1; color: $text-muted; padding: 0 2; }
    """

    BINDINGS = [
        Binding("ctrl+c", "copy", "в буфер", priority=True),
        Binding("ctrl+s", "save", "сохранить в banner.txt", priority=True),
        Binding("f1", "help", "справка", priority=True),
        Binding("ctrl+q", "quit", "выход", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.cfg = engine.load_config()
        self.all_fonts = engine.list_fonts()
        self.visible_fonts: list[str] = []
        self.current_font = "Standard"
        self.art = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="text-row"):
            yield Input(
                value=self.cfg["text"],
                placeholder="Текст баннера…",
                id="text-input",
            )
            yield Input(
                value=str(self.cfg["indent"]),
                placeholder="отступ",
                id="indent-input",
            )
        with Horizontal(id="body"):
            with Vertical(id="font-col"):
                yield Input(placeholder="поиск шрифта…", id="font-search")
                yield OptionList(id="font-list")
            yield Static(id="preview")
        yield Static(id="status")
        yield Footer()

    # ── запуск ────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.title = "banner-gen"
        try:
            self.current_font = engine.resolve_font(self.cfg["font"])
        except ValueError:
            self.current_font = "Standard"
        self._rebuild_fonts("")
        self._update_preview()

    # ── шрифты ────────────────────────────────────────────────────────

    def _rebuild_fonts(self, query: str) -> None:
        q = query.lower()
        self.visible_fonts = [f for f in self.all_fonts if q in f.lower()]
        option_list = self.query_one("#font-list", OptionList)
        option_list.clear_options()
        options = self._rebuild_options(self.visible_fonts)
        option_list.add_options(options)
        if self.current_font in self.visible_fonts:
            option_list.highlighted = self.visible_fonts.index(self.current_font)
        elif self.visible_fonts:
            option_list.highlighted = 0
            # событие подсветки может не дёрнуться при первом выставлении — обновим сами
            self.current_font = self.visible_fonts[0]
            self._update_preview()

    def _rebuild_options(self, names: list[str]) -> list[Option]:
        return [Option(name, id=f"f{i}") for i, name in enumerate(names)]

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "font-search":
            self._rebuild_fonts(event.value)
        else:
            self._update_preview()

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        idx = int(str(event.option.id).lstrip("f"))
        if 0 <= idx < len(self.visible_fonts):
            self._select_font(self.visible_fonts[idx])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.on_option_list_option_highlighted(event)  # type: ignore[arg-type]

    def _select_font(self, font: str) -> None:
        if font == self.current_font:
            return
        self.current_font = font
        self._update_preview()

    # ── превью ────────────────────────────────────────────────────────

    def _params(self) -> tuple[str, int]:
        try:
            text = self.query_one("#text-input", Input).value
            indent_raw = self.query_one("#indent-input", Input).value
        except Exception:  # виджеты уже удалены (on_unmount)
            return str(self.cfg.get("text", "")), int(self.cfg.get("indent", 0))
        try:
            indent = max(0, int(indent_raw or 0))
        except ValueError:
            indent = 0
        return text, indent

    def _update_preview(self) -> None:
        text, indent = self._params()
        preview = self.query_one("#preview", Static)
        status = self.query_one("#status", Static)
        if not text:
            self.art = ""
            preview.update(Text("Введите текст баннера", style="dim"))
            status.update(Text(""))
            return
        try:
            self.art = engine.render(text, self.current_font, indent)
        except Exception as exc:  # noqa: BLE001
            self.art = ""
            preview.update(Text(f"Не удалось отрендерить: {exc}", style="red"))
            status.update(Text(""))
            return
        preview.update(Text(self.art, no_wrap=True))
        lines = self.art.splitlines() or [""]
        width = max(len(line) for line in lines)
        note = f"{self.current_font} · {width}×{len(lines)}"
        if width > WIDTH_HINT:
            note += f"  ⚠ шире {WIDTH_HINT} колонок — в консоли может перенестись"
            status.update(Text(note, style="yellow"))
        else:
            status.update(Text(note))

    # ── действия ──────────────────────────────────────────────────────

    def action_copy(self) -> None:
        if not self.art:
            self.notify("Нечего копировать", severity="warning")
            return
        try:
            engine.copy_to_clipboard(self.art)
            self.notify("Скопировано в буфер обмена")
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Буфер обмена недоступен: {exc}", severity="error")

    def action_save(self) -> None:
        if not self.art:
            self.notify("Нечего сохранять", severity="warning")
            return
        default = self.cfg["last_path"] or "banner.txt"
        self.push_screen(SaveDialog(default), self._do_save)

    def action_help(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.screen.dismiss(None)
        else:
            self.push_screen(HelpScreen())

    def _do_save(self, path: str | None) -> None:
        if not path:
            return
        try:
            saved = engine.save(path, self.art)
        except OSError as exc:
            self.notify(f"Не удалось сохранить: {exc}", severity="error")
            return
        self.cfg["last_path"] = str(saved)
        engine.save_config(self._current_cfg())
        self.notify(f"Сохранено: {saved}")

    def _current_cfg(self) -> dict:
        text, indent = self._params()
        self.cfg.update(text=text, font=self.current_font, indent=indent)
        return self.cfg

    def on_unmount(self) -> None:
        engine.save_config(self._current_cfg())


if __name__ == "__main__":
    BannerApp().run()
