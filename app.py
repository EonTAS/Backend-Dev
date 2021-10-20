import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/home")
def get_home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # if POST request then attempt to register
    if request.method == "POST":
        username = request.form.get("username").lower()
        # see if a user by same name already exists
        existing = mongo.db.users.find_one({"username": username})
        if existing:
            # regect user creation if name already exists
            flash("user already exists")
            return redirect(url_for("register"))

        # construct an entry in users database with hashed password
        user = {
            "username": username,
            "password": generate_password_hash(request.form.get("password")),
            "balance": 0.0
        }
        mongo.db.users.insert_one(user)

        # fix session cookies to have logged in user
        session["user"] = username
        session["basket"] = []
        flash("registration successful")
        return redirect(url_for("get_store"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # if someone already logged in, log out and then go to login page
    if session.get("user"):
        logout()

    # if POST then attempt to log in
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")

        # get user from users database with same username
        existing = mongo.db.users.find_one({"username": username})

        # if entry doesnt exist or password has doesnt match,
        # then redirect to login page again
        if existing and check_password_hash(existing["password"], password):
            # log in session cookies set and tell user logged in
            session["user"] = username
            session["basket"] = []
            flash(f'logged in as {username}')
            return redirect(url_for("get_store"))

        flash("incorrect username or pasword")

    return render_template("login.html")


@app.route("/logout")
def logout():
    # empty session and tell user its logged out
    session.clear()
    flash("Logged Out")
    return redirect(url_for("get_store"))


@app.route("/user/<username>", methods=["GET", "POST"])
def get_user(username):
    # allows requesting arbritary user
    if request.method == "POST":
        # if post request then user wanting to deposit money
        deposit_value = float(request.form.get("deposit"))
        update_balance(username, deposit_value)
        flash(f'£{deposit_value:.2f} deposited')

    user = mongo.db.users.find_one({"username": username})
    if not user:
        # if user requested doesnt exist, redirect to the logged in user
        if session.get("user"):
            return redirect(url_for("get_user", username=session["user"]))
        return redirect(url_for("login"))
    # get every item of stock the user has bought
    items = list(mongo.db.stock.find({"boughtBy": username, "sold": True}))

    # saves if requested user is the logged in user or if the user is admin
    logged_in = username == session.get("user", "")
    logged_in = logged_in or session.get("user", "") == "admin"
    return render_template("user.html",
                           user=user,
                           logged_in=logged_in,
                           items=items)


@app.route("/deleteUser/<username>")
def delete_account(username):
    # only allow deleting if logged in user is admin
    # or if they are the user trying to delete themself
    if username == session["user"] or session["user"] == "admin":
        mongo.db.users.delete_one({"username": username})
        session.clear()
        flash("user deleted")
        return redirect(url_for("get_store"))
    flash("hey you're not admin stop that")
    return redirect(url_for("get_store"))


@app.route("/")
@app.route("/store", methods=["GET", "POST"])
def get_store():
    shop = list(mongo.db.stock.find())
    for item in shop:  # create a comparable id entry in data since jinja sucks
        item["id"] = str(item["_id"])
    return render_template("store.html", shop=shop)


@app.route("/edit/<item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    if session.get("user", "") == "admin":  # only allow edit if admin
        # request form already follows correct format for data in database,
        # so get that into dict
        item = request.form.to_dict()
        item["sold"] = bool(item["boughtBy"])
        mongo.db.stock.update_one({"_id": ObjectId(item_id)}, {"$set": item})
    return redirect(url_for("get_store"))


@app.route("/newItem/", methods=["GET", "POST"])
def new_item():
    if session.get("user", "") == "admin":  # only allow add if admin
        # request form already follows correct format for data in database,
        # so get that into dict
        item = request.form.to_dict()
        item["sold"] = bool(item["boughtBy"])
        mongo.db.stock.insert_one(item)
    return redirect(url_for("get_store"))


@app.route("/delete/<product_id>")
def delete_item(product_id):
    if session.get("user", "") == "admin":  # only allow delete if admin
        mongo.db.stock.remove({"_id": ObjectId(product_id)})  # delete item
        flash("item removed from stock")
        return redirect(url_for("get_store"))
    return redirect(url_for("get_store"))


@app.route("/purchase/<product_id>")
def add_basket(product_id):
    if product_id not in session["basket"]:
        session["basket"].append(product_id)  # add item to session cookies
        session.modified = True  # mark session as modified so that it saves
        flash("added to basket")
    return redirect(request.referrer)


@app.route("/remove/<product_id>")
def remove_basket(product_id):
    if product_id in session["basket"]:
        session["basket"].remove(product_id)  # remove item from session
        session.modified = True  # mark session as modified so that it saves
        flash("removed from basket")
    return redirect(request.referrer)


@app.route("/cart")
def get_cart():
    # creates a query that returns every item in the sessions basket
    q = {"_id": {"$in": [ObjectId(id) for id in session["basket"]]}}
    basket = list(mongo.db.stock.find(q))

    # sum item costs quickly
    cost = sum(float(item["cost"]) for item in basket)
    balance = get_balance(session["user"])
    return render_template("basket.html",
                           basket=basket,
                           totalCost=cost,
                           balance=balance)


@app.route("/sendPurchase")
def purchase_all():
    # creates a query that returns every item in the sessions basket
    q = {"_id": {"$in": [ObjectId(id) for id in session["basket"]]}}
    basket = list(mongo.db.stock.find(q))
    # sum item costs quickly
    cost = sum(float(item["cost"]) for item in basket)
    # only buy if can afford to
    if cost <= get_balance(session["user"]):
        # updates every item to be bought
        bought = {"$set": {"boughtBy": session["user"], "sold": True}}
        mongo.db.stock.update_many(q, bought)
        session["basket"] = []
        update_balance(session["user"], -cost)
        flash("items bought")

    return redirect(url_for("get_user", username=session["user"]))


# queries DB for user balance
def get_balance(username):
    user = mongo.db.users.find_one({"username": username}, {"balance": 1})
    return user.get("balance", 0)


# updates DB with user balance
def update_balance(username, change):
    user = mongo.db.users.find_one({"username": username}, {"balance": 1})
    curr_balance = user.get("balance", 0)
    new_balance = curr_balance + change
    mongo.db.users.update_one(
        {"username": username}, {"$set": {"balance": new_balance}}
        )


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
