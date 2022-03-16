from fabric.api import local


def run():
    local("export DB_NAME=default;  poetry run uvicorn app.main:app --port 8000 --reload")


def lint(path="."):
    local(f"poetry run isort {path}")
    local(f"poetry run black {path}")
    local(f"poetry run flake8 {path}")


def test(path="."):
    local(f"export DB_NAME=test; poetry run pytest -s {path}")
