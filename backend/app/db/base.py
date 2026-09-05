"""
Import point for Alembic autogenerate.
Imports all models so `alembic revision --autogenerate` can discover them via Base.metadata.
"""
from app.db.session import Base  # noqa: F401
from app.models.video import Video  # noqa: F401

__all__ = ["Base", "Video"]
