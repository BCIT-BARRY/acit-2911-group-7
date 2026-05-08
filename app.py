"""
flask; python web application framework
request; allows us to retrieve data from user
render_template; allows us to render html pages from templates folder
redirect; allows us to send user to another route/page
url_for; builds the URL for a route function
flask.typing ResponseReturnValue; keeps code clean by type checking flask response objects
"""

#! NOTE: All code will be as explicit as possible for the purposes of learning
from flask import Flask, request, render_template, redirect, url_for
from flask.typing import ResponseReturnValue

# instantiate flask, and templates folder location
app = Flask(__name__, template_folder="templates")


# route; get index page
# route; post for login
@app.route("/", methods=["GET", "POST"])
def index() -> tuple[str, int] | ResponseReturnValue:
    if request.method == "GET":
        return render_template("index.html"), 200

    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # TODO; Hardcoded for now, database WIP.
        if username == "barry" and password == "1234":
            return redirect(url_for("create_portfolio"))
            # return "Successfully logged in", 200

    return "Unsuccessful.", 200


# route; get create_portfolio page
# route; post create_portfolio for creating portfolio
@app.route("/create_portfolio", methods=["GET", "POST"])
def create_portfolio() -> tuple[str, int]:
    if request.method == "GET":
        return render_template("create_portfolio.html"), 200

    # TODO; Save to database later.
    elif request.method == "POST":
        portfolio_name = request.form["portfolio_name"]
        portfolio_cash_amount = request.form["portfolio_cash_amount"]
        return "Successfully created the Portfolio Account.", 201

    return "WIP", 200


# route; portfolio, get portfolio account details
@app.route("/portfolio", methods=["GET"])
def portfolio() -> tuple[str, int]:
    return render_template("portfolio.html"), 200


# runs app in debug mode.
if __name__ == "__main__":
    app.run(debug=True)
