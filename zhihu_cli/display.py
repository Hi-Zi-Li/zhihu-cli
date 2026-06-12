"""Terminal display utilities for zhihu-cli.

This module keeps user-facing output safe on Windows consoles that still use
legacy encodings such as GBK. All helper functions preserve the existing API
surface used across the CLI.
"""

from __future__ import annotations

import os
import re
import sys
from html import unescape

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

ZHIHU_THEME = Theme(
    {
        "info": "dim cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "title": "bold cyan",
        "subtitle": "dim white",
        "accent": "bold blue",
        "muted": "dim",
        "stat.key": "cyan",
        "stat.value": "white",
        "badge": "bold magenta",
    }
)

console = Console(theme=ZHIHU_THEME)

BRAND = "[bold blue]zhihu[/bold blue][bold white]-cli[/bold white]"
SEPARATOR = "[dim]" + ("=" * 50) + "[/dim]"

_ASCII_FALLBACKS = {
    "✓": "[OK]",
    "✗": "[ERR]",
    "›": ">",
    "…": "...",
    "—": "-",
    "•": "*",
    "·": ".",
    "○": "o",
    "→": "->",
    "←": "<-",
    "▸": ">",
    "万": "w",
    "亿": "y",
}


def _stdout_encoding() -> str:
    encoding = getattr(sys.stdout, "encoding", None)
    if encoding:
        return encoding
    return os.device_encoding(1) or "utf-8"


def _sanitize_console_text(text: str) -> str:
    """Replace symbols that cannot be encoded by the active console."""
    encoding = _stdout_encoding()
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        pass

    sanitized = text
    for src, dst in _ASCII_FALLBACKS.items():
        sanitized = sanitized.replace(src, dst)
    return sanitized


def print_banner() -> None:
    """Print a branded banner."""
    ver = _get_version()
    subtitle = _sanitize_console_text("Zhihu terminal client - Search, Read, Interact")
    console.print(
        Panel(
            f"{BRAND}  [dim]v{ver}[/dim]\n[dim]{subtitle}[/dim]",
            border_style="blue",
            padding=(0, 2),
        ),
        highlight=False,
    )


def _get_version() -> str:
    from . import __version__

    return __version__


def print_success(msg: str) -> None:
    """Print a success message."""
    console.print(_sanitize_console_text(f"  [success]✓[/success] {msg}"))


def print_error(msg: str) -> None:
    """Print an error message."""
    console.print(_sanitize_console_text(f"  [error]✗[/error] {msg}"))


def print_warning(msg: str) -> None:
    """Print a warning message."""
    console.print(_sanitize_console_text(f"  [warning]![/warning] {msg}"))


def print_info(msg: str) -> None:
    """Print an informational message."""
    console.print(_sanitize_console_text(f"  [info]›[/info] {msg}"))


def print_hint(msg: str) -> None:
    """Print a hint message."""
    console.print(_sanitize_console_text(f"  [muted]hint: {msg}[/muted]"))


def strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return unescape(clean).strip()


def format_count(count: int | str) -> str:
    """Format large numbers for display."""
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            return str(count)
    if count >= 100_000_000:
        return f"{count / 100_000_000:.1f}y"
    if count >= 10_000:
        return f"{count / 10_000:.1f}w"
    return str(count)


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ASCII ellipsis."""
    if not text:
        return ""
    text = text.replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def make_table(title: str, *, show_lines: bool = False, pad_edge: bool = False) -> Table:
    """Create a branded Table with standard styling."""
    return Table(
        title=f"[title]{_sanitize_console_text(title)}[/title]",
        title_style="",
        border_style="blue",
        header_style="bold cyan",
        show_lines=show_lines,
        pad_edge=pad_edge,
        expand=False,
    )


def make_kv_table(title: str) -> Table:
    """Create a key-value profile table."""
    table = Table(
        title=f"[title]{_sanitize_console_text(title)}[/title]",
        title_style="",
        border_style="blue",
        show_header=False,
        pad_edge=False,
        expand=False,
    )
    table.add_column("Key", style="stat.key", width=12, justify="right")
    table.add_column("Value", style="stat.value")
    return table


def format_stats_line(pairs: dict[str, str | int]) -> str:
    """Create an inline stats display."""
    parts = []
    for label, value in pairs.items():
        parts.append(
            _sanitize_console_text(
                f"[dim]▸[/dim] [white]{format_count(value)}[/white] [dim]{label}[/dim]"
            )
        )
    return "  ".join(parts)
