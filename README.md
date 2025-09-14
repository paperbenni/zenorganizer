# Zenorganizer

Zenorganizer is an AI-powered personal organizer that runs as a Telegram bot. It uses multiple AI agents to help you manage tasks, notes, and reminders through natural conversation.

## Features

- **Telegram Bot Interface:** Interact through Telegram with secure chat ID authorization
- **Multi-Agent AI System:** Uses specialized AI agents for chat, memory management, and reminders
- **Smart Memory Management:** Automatic deduplication, aggregation, and garbage collection of stored information
- **Periodic Maintenance:** Background agents clean up and optimize memories every 10 hours
- **Scheduled Reminders:** AI-powered reminder system that checks every 15 minutes
- **Database Storage:** SQLite database with Alembic migrations for schema management
- **Web API:** FastAPI endpoints for debugging and manual agent execution
- **Containerized Dependencies:** Docker Compose for optional NocoDB integration

## Project Structure

- `zeno/`: The main Python package containing the application logic.
- `alembic/`: Contains the Alembic database migration scripts.
- `data/`: Directory for storing the SQLite database and other data.
- `tests/`: Test files for the application.
- `justfile`: Defines commands for common development tasks.
- `pyproject.toml`: Defines project dependencies and tool configurations.
- `docker-compose.yml`: Defines external services (NocoDB) for development.
- `CLAUDE.md`: Developer documentation for AI assistants working on this codebase.

## Getting Started

### Prerequisites

- Python 3.13 or later
- `uv` package manager
- `just` command runner (optional, but recommended)
- Docker (optional, for NocoDB)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/paperbenni/zenorganizer.git
    cd zenorganizer
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

3.  **Set up environment variables:**
    - Copy the example environment file:
      ```bash
      cp example.env .env
      ```
    - Edit `.env` and add your configuration:
      - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
      - `TELEGRAM_CHAT_ID`: Your Telegram chat ID (required for security)
      - `OPENAI_API_KEY`: OpenAI API key (required)
      - `MODEL_NAME`: AI model name (e.g., `gpt-4`)
      - `OPENAI_BASE_URL`: Custom OpenAI API base URL (optional)
      - `LOGFIRE_TOKEN`: Logfire monitoring token (optional)

4.  **Initialize the database:**
    ```bash
    just alembic-upgrade
    ```
    or directly:
    ```bash
    uv run alembic upgrade head
    ```

## Usage

### Running the Application

- **Start the bot and web API:**
  ```bash
  just run
  ```
  or directly:
  ```bash
  uv run main.py
  ```

### Development

- **Format code:**
  ```bash
  just format
  ```

- **Lint and type check:**
  ```bash
  just check
  ```

- **Run tests:**
  ```bash
  uv run pytest
  ```

### Database Management

- **Create migration (after model changes):**
  ```bash
  just alembic-revision message="describe changes"
  ```

- **Apply migrations:**
  ```bash
  just alembic-upgrade
  ```

### Optional Services

- **Start NocoDB (for database management):**
  ```bash
  just start-nocodb
  ```

### Web API Debugging

The application includes a FastAPI web server (port 8001) for debugging:

- `GET /memories` - View stored memories
- `GET /old_messages` - View message history
- `POST /deduplicate?wait=1` - Run deduplication agent
- `POST /aggregate?wait=1` - Run aggregation agent
- `POST /split?wait=1` - Run splitting agent
- `POST /garbage_collect?wait=1` - Run garbage collection
- `POST /reminders?wait=1` - Run reminder agent

## Architecture

### AI Agents
The system uses multiple specialized AI agents powered by `pydantic_ai`:

- **Chat Agent**: Handles user conversations, stores relevant information as memories
- **Deduplicator**: Removes duplicate and contradictory memories
- **Aggregator**: Combines related memories into cohesive entries
- **Splitter**: Separates over-aggregated memories when appropriate
- **Garbage Collector**: Removes outdated and completed reminders
- **Reminder Agent**: Sends timely reminders based on stored memories

### Background Processes
- **Maintenance Cycle**: Runs every 10 hours to optimize memory storage
- **Reminder Checks**: Runs every 15 minutes to send due reminders
- **Web API**: FastAPI server for debugging and manual agent execution

### Data Flow
1. User sends message via Telegram
2. Chat agent processes message and stores relevant information
3. Background agents periodically optimize memory storage
4. Reminder agent checks and sends time-sensitive notifications
5. All interactions are logged for context preservation

## Security
- Telegram chat ID authorization prevents unauthorized access
- No default credentials - all required configuration must be explicitly set
- Environment-based configuration for sensitive data

## Future Improvements

### Planned Features
- [ ] Web interface with authentication
- [ ] Multi-user support (currently single-user with fixed chat ID)
- [ ] User management system
- [ ] Improved time zone handling (currently Europe/Berlin only)

### Technical Improvements
- [ ] Production deployment configuration
- [ ] Webhook-based Telegram bot delivery (currently polling)
- [ ] Enhanced testing coverage
- [ ] Performance optimization for large memory sets
- [ ] Backup and export functionality

### Known Issues
- [ ] Time format improvements (AM/PM handling)
- [ ] Memory relevance scoring implementation (currently unused)
- [ ] Better error handling and retry mechanisms
