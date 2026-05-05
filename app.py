'''imports modules
- flask allows us to use the python webframe application
- render_templates allows us to use .html pages
- url_for allows us to directly link  back to .html pages
'''
from flask import Flask, render_template, url_for

# instantiate flask
app = Flask(__name__)

# ROUTE: GET INDEX PAGE 
@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
def index():
    return render_template("index.html")

# ROUTE: GET ABOUT PAGE
@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html", title="About")

# ROUTE: GET CONTACT PAGE
@app.route("/contact", methods=["GET"])
def contact():
    return render_template("contact.html", title="Contact")

# ROUTE: GET LOGIN PAGE
@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html", title="Login")

# ROUTE: GET PORTFOLIO PAGE
@app.route("/portfolio", methods=["GET"])
def portfolio():
    return render_template("/portfolio.html", title="Portfolio")

# start app
if __name__ == "__main__":
    app.run(debug=True)