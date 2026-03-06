from flask import Flask, render_template

app: Flask = Flask(__name__)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/stack-calculator")
def stack_calculator() -> str:
    return render_template("stack_calculator.html")


if __name__ == "__main__":
    app.run(debug=True)
