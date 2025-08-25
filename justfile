
format:
    uvx black zeno

check:
    uvx pyrefly check

run:
    uv run main.py

deploy:
    git pull
    just run
