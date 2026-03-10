import os
from typing import Any

from flask import Flask, render_template

app: Flask = Flask(__name__)


@app.context_processor
def inject_env() -> dict[str, Any]:
    return {"app_env": os.environ.get("APP_ENV", "dev")}


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/stack-calculator")
def stack_calculator() -> str:
    return render_template("stack_calculator.html")


if __name__ == "__main__":
    app.run(debug=True)
