set dotenv-load := true

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

# nocodb helpers
ensure-data-dir:
    mkdir -p ./data && chown ${PUID:-1000}:${PGID:-1000} ./data || true

nocodb-up:
    docker compose up -d

nocodb-down:
    docker compose down

start-nocodb:
    just ensure-data-dir
    just nocodb-up


# shortcuts
e:
    uv run nvim .
