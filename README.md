# Zenorganizer

Zenorganizer is an AI chatbot designed to help you organize your life. It provides a conversational interface to manage your tasks, notes, and other information through Telegram.

## Features

- **Telegram Bot Interface:** Interact with the organizer through Telegram.
- **AI-Powered:** Utilizes AI for natural language understanding and task management.
- **Database Storage:** Uses a database to store your information, with Alembic for migrations.
- **Containerized Dependencies:** Uses Docker to manage external services like NocoDB.

## Project Structure

- `zeno/`: The main Python package containing the application logic.
- `alembic/`: Contains the Alembic database migration scripts.
- `data/`: Directory for storing data, such as the database file.
- `justfile`: Defines commands for common development tasks.
- `pyproject.toml`: Defines project dependencies and tool configurations.
- `docker-compose.yml`: Defines external services for the development environment.

## Getting Started

### Prerequisites

- Python 3.13 or later
- `uv` package manager
- `just` command runner
- Docker

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/paperbenni/zenorganizer.git
    cd zenorganizer
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    uv sync
    ```

3.  **Set up your environment variables:**
    - Copy the `example.env` file to `.env`:
      ```bash
      cp example.env .env
      ```
    - Edit the `.env` file and add your API keys and other configuration.

4.  **Run the database migrations:**
    ```bash
    just alembic-upgrade
    ```

## Usage

- **Run the application:**
  ```bash
  just run
  ```

- **Format the code:**
  ```bash
  just format
  ```

- **Check the code for issues:**
  ```bash
  just check
  ```

- **Start the NocoDB service:**
  ```bash
  just start-nocodb
  ```

## TODO

- [ ] Run memory gardeners on schedule
- [ ] Web interface
    - [ ] auth
    - [ ] add telegram users
- [ ] User management
    - [ ] Make memories user specific
    - [ ] Do not hardcode user ids
- [ ] Logfire thingy
- [ ] Solve time zone confusion
- [ ] AM/PM thingy
