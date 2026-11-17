"""Isolate every test run from the real database and scan storage.

Loaded by pytest before any test module, so the settings singleton (created on the first import of
app.core.config) always points at a temporary data directory, whichever test module is collected first.
"""
import os
import tempfile

os.environ.setdefault("TRUTHLENS_DATA_DIR", tempfile.mkdtemp(prefix="detective-test-"))
