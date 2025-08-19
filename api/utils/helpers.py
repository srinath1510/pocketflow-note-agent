"""
Utility helper functions
"""
import json
import hashlib
from datetime import datetime
from typing import Any
from .storage import content_hashes


def serialize_for_json(obj):
    """Convert datetime objects and other non-serializable objects to JSON-safe formats"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_for_json(item) for item in obj)
    elif isinstance(obj, set):
        return list(serialize_for_json(item) for item in obj)
    elif hasattr(obj, '__dict__'):
        return serialize_for_json(obj.__dict__)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        try:
            return [serialize_for_json(item) for item in obj]
        except:
            return str(obj)
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


def hash_content(content: str) -> str:
    """Create hash of content to detect duplicates"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def is_duplicate_content(note_content: str) -> bool:
    """Check if content is duplicate"""
    content_hash = hash_content(note_content)
    if content_hash in content_hashes:
        return True
    content_hashes.add(content_hash)
    return False