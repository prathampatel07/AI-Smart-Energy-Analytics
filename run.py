from app import create_app


app = create_app()

if __name__ == "__main__":
    # Dev server (local only). For “live” use `python run_prod.py`.
    app.run(host="127.0.0.1", port=5000, debug=True)
