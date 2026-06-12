"""Machine-readable hydrate command for Zhihu entities."""

from __future__ import annotations

import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from typing import Any

import click

from ..display import console, print_error, strip_html
from .content import _get_client


@click.command()
@click.argument("entity_type", type=click.Choice(["question", "answer", "article"]))
@click.argument("item_id", type=str)
@click.option("-c", "--comment-limit", default=5, show_default=True, help="Maximum comments to include")
@click.option("-a", "--answer-limit", default=3, show_default=True, help="Top answers to include for question hydrate")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def hydrate(entity_type: str, item_id: str, comment_limit: int, answer_limit: int, as_json: bool):
    """Fetch machine-readable detail for question/answer/article hydration."""
    with _get_client() as client:
        try:
            payload = _build_hydrate_payload(
                client=client,
                entity_type=entity_type,
                item_id=item_id,
                comment_limit=comment_limit,
                answer_limit=answer_limit,
            )
        except Exception as exc:
            print_error(f"Failed to hydrate {entity_type}: {exc}")
            sys.exit(1)

    if as_json:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    title = _payload_title(payload)
    console.print(
        f"Hydrated [{entity_type}] {title} "
        f"({len(payload.get('comments', []))} comments)"
    )


def _build_hydrate_payload(
    *,
    client: Any,
    entity_type: str,
    item_id: str,
    comment_limit: int,
    answer_limit: int,
) -> dict[str, Any]:
    if entity_type == "question":
        question = client.get_question(item_id)
        answers = client.get_question_answers(item_id, limit=answer_limit).get("data", [])
        warnings: list[dict[str, str]] = []
        if comment_limit > 0:
            warnings.append(
                {
                    "code": "question_comments_not_included",
                    "message": "Question hydrate currently includes question detail and top answers only.",
                }
            )
        return {
            "mode": "hydrate",
            "entity_type": "question",
            "question": _normalize_question(question),
            "answers": [_normalize_answer(answer) for answer in answers if isinstance(answer, dict)],
            "comments": [],
            "warnings": warnings,
        }

    if entity_type == "answer":
        answer = client.get_answer(item_id)
        comments = []
        if comment_limit > 0:
            comments = client.get_answer_comments(item_id, limit=comment_limit).get("data", [])
        return {
            "mode": "hydrate",
            "entity_type": "answer",
            "answer": _normalize_answer(answer),
            "comments": [_normalize_comment(comment) for comment in comments if isinstance(comment, dict)],
            "warnings": [],
        }

    article = client.get_article(item_id)
    comments = []
    if comment_limit > 0:
        comments = client.get_article_comments(item_id, limit=comment_limit).get("data", [])
    return {
        "mode": "hydrate",
        "entity_type": "article",
        "article": _normalize_article(article),
        "comments": [_normalize_comment(comment) for comment in comments if isinstance(comment, dict)],
        "warnings": [],
    }


def _normalize_question(question: dict[str, Any]) -> dict[str, Any]:
    topics = question.get("topics", [])
    detail_html = question.get("detail", "")
    detail_blocks = _extract_content_blocks(detail_html)
    return {
        "id": str(question.get("id", "")),
        "title": strip_html(question.get("title", "")),
        "detail": _content_blocks_to_text(detail_blocks),
        "answer_count": _safe_int(question.get("answer_count")),
        "follower_count": _safe_int(question.get("follower_count")),
        "visit_count": _safe_int(question.get("visit_count")),
        "comment_count": _safe_int(question.get("comment_count")),
        "url": f"https://www.zhihu.com/question/{question.get('id', '')}",
        "images": _content_block_images(detail_blocks),
        "content_blocks": detail_blocks,
        "topics": [
            topic.get("name", "")
            for topic in topics
            if isinstance(topic, dict) and topic.get("name")
        ],
    }


def _normalize_answer(answer: dict[str, Any]) -> dict[str, Any]:
    author = answer.get("author", {}) if isinstance(answer.get("author"), dict) else {}
    question = answer.get("question", {}) if isinstance(answer.get("question"), dict) else {}
    content = answer.get("content", "") or answer.get("excerpt", "")
    content_blocks = _extract_content_blocks(content)
    return {
        "id": str(answer.get("id", "")),
        "title": strip_html(question.get("title", "")),
        "body": _content_blocks_to_text(content_blocks),
        "excerpt": strip_html(answer.get("excerpt", "") or content)[:400],
        "author": {
            "id": str(author.get("id", "")),
            "name": author.get("name", "Anonymous"),
        },
        "voteup_count": _safe_int(answer.get("voteup_count")),
        "comment_count": _safe_int(answer.get("comment_count")),
        "url": f"https://www.zhihu.com/answer/{answer.get('id', '')}",
        "images": _content_block_images(content_blocks),
        "content_blocks": content_blocks,
    }


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    author = article.get("author", {}) if isinstance(article.get("author"), dict) else {}
    content = article.get("content", "")
    content_blocks = _extract_content_blocks(content)
    return {
        "id": str(article.get("id", "")),
        "title": strip_html(article.get("title", "")),
        "body": _content_blocks_to_text(content_blocks),
        "excerpt": strip_html(article.get("excerpt", "") or content)[:400],
        "author": {
            "id": str(author.get("id", "")),
            "name": author.get("name", "Anonymous"),
        },
        "voteup_count": _safe_int(article.get("voteup_count")),
        "comment_count": _safe_int(article.get("comment_count")),
        "url": f"https://zhuanlan.zhihu.com/p/{article.get('id', '')}",
        "images": _content_block_images(content_blocks),
        "content_blocks": content_blocks,
    }


def _normalize_comment(comment: dict[str, Any]) -> dict[str, Any]:
    author_value = comment.get("author")
    author_name = ""
    author_id = ""
    if isinstance(author_value, dict):
        member = author_value.get("member", {}) if isinstance(author_value.get("member"), dict) else {}
        author_name = (
            author_value.get("name")
            or member.get("name")
            or member.get("headline")
            or ""
        )
        author_id = str(author_value.get("id") or member.get("id") or "")
    elif isinstance(author_value, str):
        author_name = author_value

    return {
        "id": str(comment.get("id", "")),
        "author": {
            "id": author_id,
            "name": author_name or "Anonymous",
        },
        "content": strip_html(comment.get("content", "")),
        "vote_count": _safe_int(comment.get("vote_count")),
        "reply_count": _safe_int(
            comment.get("reply_comment_count")
            or comment.get("child_comment_count")
            or comment.get("child_comment_total_count")
        ),
    }


def _strip_html_preserve_blocks(text: str) -> str:
    if not text:
        return ""

    cleaned = str(text)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(p|div|section|article|blockquote|pre|h[1-6]|tr)>", "\n", cleaned)
    cleaned = re.sub(r"(?i)<li[^>]*>", "- ", cleaned)
    cleaned = re.sub(r"(?i)</li>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = unescape(cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


class _ContentBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, str]] = []
        self._text_parts: list[str] = []
        self._skip_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style"}:
            self._skip_tag = lowered
            return
        if self._skip_tag is not None:
            return
        if lowered == "img":
            self._flush_text()
            url = _extract_img_attrs_url(attrs)
            if url and not _is_duplicate_adjacent_image(self.blocks, url):
                self.blocks.append({"type": "image", "url": url})
            return
        if lowered == "br":
            self._text_parts.append("\n")
            return
        if lowered == "li":
            self._text_parts.append("- ")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._skip_tag == lowered:
            self._skip_tag = None
            return
        if self._skip_tag is not None:
            return
        if lowered in {"p", "div", "section", "article", "blockquote", "pre", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush_text()

    def handle_data(self, data: str) -> None:
        if self._skip_tag is not None or not data:
            return
        self._text_parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush_text()

    def _flush_text(self) -> None:
        if not self._text_parts:
            return
        text = _normalize_block_text("".join(self._text_parts))
        self._text_parts.clear()
        if not text:
            return
        if self.blocks and self.blocks[-1].get("type") == "text":
            self.blocks[-1]["text"] = f"{self.blocks[-1].get('text', '')}\n\n{text}".strip()
            return
        self.blocks.append({"type": "text", "text": text})


def _extract_content_blocks(text: str) -> list[dict[str, str]]:
    if not text:
        return []
    parser = _ContentBlockParser()
    parser.feed(str(text))
    parser.close()
    return parser.blocks


def _content_blocks_to_text(blocks: list[dict[str, str]]) -> str:
    parts = [
        str(block.get("text", "")).strip()
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text" and str(block.get("text", "")).strip()
    ]
    return "\n\n".join(parts).strip()


def _content_block_images(blocks: list[dict[str, str]]) -> list[str]:
    urls: list[str] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "image":
            continue
        url = _normalize_media_url(str(block.get("url", "")))
        if url and url not in urls:
            urls.append(url)
    return urls


def _extract_image_urls(text: str) -> list[str]:
    if not text:
        return []
    urls: list[str] = []
    for tag in re.findall(r"""<img\b[^>]*>""", str(text), flags=re.IGNORECASE):
        url = _extract_img_tag_url(tag)
        if url and url not in urls:
            urls.append(url)
    return urls


def _extract_img_tag_url(tag: str) -> str:
    for attribute in ("data-original", "data-actualsrc", "src"):
        match = re.search(
            rf"""{attribute}=["']([^"']+)["']""",
            tag,
            flags=re.IGNORECASE,
        )
        if match:
            return _normalize_media_url(match.group(1))
    return ""


def _extract_img_attrs_url(attrs: list[tuple[str, str | None]]) -> str:
    attr_map = {str(key or "").lower(): str(value or "") for key, value in attrs}
    for attribute in ("data-original", "data-actualsrc", "src"):
        url = _normalize_media_url(attr_map.get(attribute, ""))
        if url:
            return url
    return ""


def _normalize_block_text(text: str) -> str:
    cleaned = unescape(str(text))
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    cleaned = re.sub(r"[ \t\f\v]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _is_duplicate_adjacent_image(blocks: list[dict[str, str]], url: str) -> bool:
    if not blocks:
        return False
    previous = blocks[-1]
    return previous.get("type") == "image" and previous.get("url") == url


def _normalize_media_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("//"):
        return f"https:{text}"
    if text.startswith("http://"):
        return "https://" + text[len("http://"):]
    if text.startswith("https://"):
        return text
    return ""


def _payload_title(payload: dict[str, Any]) -> str:
    entity_type = payload.get("entity_type")
    if entity_type == "question":
        return payload.get("question", {}).get("title", "")
    if entity_type == "answer":
        return payload.get("answer", {}).get("title", "")
    return payload.get("article", {}).get("title", "")


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
