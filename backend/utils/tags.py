"""
Tag helpers: normalization and get-or-create.

Tags are lowercase slugs ([a-z0-9._-], max 50 chars) so they work unchanged
as Ansible group names and inside Prometheus label values.
"""
import re
from typing import Iterable, List, Optional, Union

from models import Tag, db

TAG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9._-]{0,49}$')
MAX_TAGS_PER_DEVICE = 25


def normalize_tag(value: str) -> str:
    """Lowercase, trim, turn whitespace into '-'. Raises ValueError if invalid."""
    if not isinstance(value, str):
        raise ValueError("Tags must be strings")
    tag = re.sub(r'\s+', '-', value.strip().lower())
    if not tag:
        raise ValueError("Tag cannot be empty")
    if not TAG_PATTERN.match(tag):
        raise ValueError(
            f"Invalid tag '{value}': use letters, numbers, '.', '_' or '-' (max 50, must start with a letter or number)"
        )
    return tag


def parse_tag_input(value: Union[None, str, Iterable[str]]) -> List[str]:
    """
    Accept a list or a comma/semicolon separated string and return a
    de-duplicated, normalized, sorted list. Raises ValueError on bad input.
    """
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r'[,;]', value)
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        raise ValueError("Tags must be a list or a comma-separated string")
    tags = sorted({normalize_tag(item) for item in items if isinstance(item, str) and item.strip()})
    if any(not isinstance(item, str) for item in items):
        raise ValueError("Tags must be strings")
    if len(tags) > MAX_TAGS_PER_DEVICE:
        raise ValueError(f"A device can have at most {MAX_TAGS_PER_DEVICE} tags")
    return tags


def resolve_tags(names: Iterable[str]) -> List[Tag]:
    """Return Tag rows for already-normalized names, creating missing ones."""
    names = list(names)
    if not names:
        return []
    existing = {t.name: t for t in Tag.query.filter(Tag.name.in_(names)).all()}
    result = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.session.add(tag)
            existing[name] = tag
        result.append(tag)
    return result


def tag_filter_values(args) -> Optional[List[str]]:
    """Read ?tag=a&tag=b (or ?tag=a,b) from request args, normalized."""
    raw = args.getlist('tag')
    if not raw:
        return None
    values = []
    for item in raw:
        values.extend(parse_tag_input(item))
    return values or None


def apply_tag_filter(query, model, tags: Optional[List[str]]):
    """Restrict a Device query to devices carrying *all* given tags."""
    if not tags:
        return query
    for name in tags:
        query = query.filter(model.tags.any(Tag.name == name))
    return query
