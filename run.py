import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Bind to 0.0.0.0 for external access, respecting dynamic ports.
    app.run(host="0.0.0.0", port=port, debug=False)
