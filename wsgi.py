"""Gunicorn entry point: `gunicorn -b 0.0.0.0:43123 wsgi:app`."""

from __future__ import annotations

import os

from applyagent.web import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "43123")), debug=False)
