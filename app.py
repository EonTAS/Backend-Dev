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


@app.route("/")
@app.route("/home")
def get_home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").lower()
        existing = mongo.db.users.find_one({"username": username})
        if existing:
            flash("user already exists")
            return redirect(url_for("register"))
        
        register = {
            "username": username,
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)
        session["user"] = username
        session["basket"] = []
        flash("registration successful")
        return redirect(url_for("get_home"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        logout()

    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        if username == password:
            session["user"] = username
            session["basket"] = []
            flash(f'logged in as {username} but secretly this time')
            return redirect(url_for("get_home"))

        existing = mongo.db.users.find_one({"username": username})
        print(generate_password_hash(password))
        if existing and check_password_hash(existing["password"], password):
            print("hi")
            session["user"] = username
            session["basket"] = []
            flash(f'logged in as {username}')
            return redirect(url_for("get_home"))
        
        flash("incorrect username or pasword")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", "")
    session["basket"] = []
    flash("Logged Out")
    return redirect(url_for("get_home"))

@app.route("/user/<username>")
def get_user(username):

    #name
    #id
    #delete account
    user = mongo.db.users.find_one({"username": session["user"]})

    

    logged_in = (username == session.get("user", "")) #only show basket info, delete account etc if true


    #view basket 
    return render_template("user.html", user=user, logged_in=logged_in)

@app.route("/store", methods=["GET", "POST"])
def store():
    if request.method == "POST" and session.get("user", "") == "admin":        
        item = request.form.to_dict()
        print(item)
        mongo.db.stock.insert_one(item)
    print(session)
    shop = list(mongo.db.stock.find())
    for item in shop:
        item["id"] = str(item["_id"])
    #have edit button on each item change bottom box from a "new" item to a "edit" item, populated with old stuff
    return render_template("store.html", shop=shop)

@app.route("/purchase/<product_id>")
def add_basket(product_id):
    if product_id not in session["basket"]:
        session["basket"].append(product_id)
    session["basket"] = session["basket"].copy()
    return redirect(url_for("store"))

@app.route("/remove/<product_id>")
def remove_basket(product_id):
    if product_id in session["basket"]:
        session["basket"].remove(product_id)
    session["basket"] = session["basket"].copy()
    return redirect(url_for("store"))


@app.route("/delete/<product_id>")
def delete_item(product_id):
    if session.get("user", "") == "admin":
        mongo.db.stock.remove({"_id": ObjectId(product_id)})
        flash("item removed from stock")
        return redirect(url_for("store"))
    flash("hey you're not admin stop that")
    print(session.get("user",""))
    return redirect(url_for("store"))

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
