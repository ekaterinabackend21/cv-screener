"""Elasticsearch connection and search services."""

from .client import search_by_embedding, search_by_field

__all__ = ["search_by_embedding", "search_by_field"]
