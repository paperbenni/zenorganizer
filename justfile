
format:
    uvx ruff format

check:
    uvx ruff check
    uvx ty check

run:
    uv run main.py

deploy:
    git pull
    just run

e:
    uv run nvim .
