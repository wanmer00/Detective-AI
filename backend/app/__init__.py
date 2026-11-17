import os

# Windows Smart App Control blocks SQLAlchemy's unsigned Cython extensions; use its pure-Python path.
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT_RUNTIME", "1")
