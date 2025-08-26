
format:
    uvx ruff format

check:
    uvx ruff check

run:
    uv run main.py

deploy:
    git pull
    just run
