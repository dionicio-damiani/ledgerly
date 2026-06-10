"""Entry point so existing tooling can keep using `uvicorn main:app`.

The real application lives in :mod:`app.main`.
"""

from app.main import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
