import os

from waitress import serve

from app import create_app


def main():
    # For LAN access, set HOST=0.0.0.0
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    threads = int(os.getenv("THREADS", "8"))

    app = create_app()
    serve(app, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()

