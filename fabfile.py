from fabric.api import local


def run():
    local("poetry run uvicorn main:app --port 8000 --reload")


def lint(path="."):
    local(f"poetry run isort {path}")
    local(f"poetry run black {path}")
    local(f"poetry run flake8 {path}")
