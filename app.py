import os

from flask import Flask, render_template

app = Flask(__name__)


@app.context_processor
def inject_env():
    return {"app_env": os.environ.get("APP_ENV", "dev")}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stack-calculator")
def stack_calculator():
    return render_template("stack_calculator.html")


if __name__ == "__main__":
    app.run(debug=True)
