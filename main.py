def main():
    # Entry point for the package — run the telegram bot and a Flask app
    # concurrently in the same process. Start the Flask dev server in a
    # background thread so both the API and the bot run together.
    import threading
    from zeno.telegram_bot import run_bot
    from zeno.api_flask import app as flask_app

    def run_flask():
        # Use Flask's built-in server for dev usage.
        flask_app.run(host="0.0.0.0", port=8001)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    run_bot()


if __name__ == "__main__":
    main()
