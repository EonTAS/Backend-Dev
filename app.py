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
            "password": generate_password_hash(request.form.get("password")),
            "balance" : 0.0
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

        existing = mongo.db.users.find_one({"username": username})
        if existing and check_password_hash(existing["password"], password):
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

@app.route("/user/<username>", methods=["GET", "POST"])
def get_user(username):
    if request.method == "POST":
        deposit_value = float(request.form.get("deposit"))
        update_balance(username, deposit_value)
        

    user = mongo.db.users.find_one({"username": session["user"]})
    #name
    #id
    #delete account

    

    logged_in = (username == session.get("user", "")) #only show basket info, delete account etc if true


    #view basket 
    return render_template("user.html", user=user, logged_in=logged_in)

@app.route("/store", methods=["GET", "POST"])
def store():
    if request.method == "POST" and session.get("user", "") == "admin":        
        item = request.form.to_dict()
        item["sold"] = False
        mongo.db.stock.insert_one(item)


    shop = list(mongo.db.stock.find())
    for item in shop:
        item["id"] = str(item["_id"])
    #have edit button on each item change bottom box from a "new" item to a "edit" item, populated with old stuff
    return render_template("store.html", shop=shop)

@app.route("/purchase/<product_id>")
def add_basket(product_id):
    if product_id not in session["basket"]:
        session["basket"].append(product_id)
        session.modified = True
        flash("added to basket")
    return redirect(request.referrer)

@app.route("/remove/<product_id>")
def remove_basket(product_id):
    if product_id in session["basket"]:
        session["basket"].remove(product_id)
        session.modified = True
        flash("removed from basket")
    return redirect(request.referrer)


@app.route("/delete/<product_id>")
def delete_item(product_id):
    if session.get("user", "") == "admin":
        mongo.db.stock.remove({"_id": ObjectId(product_id)})
        flash("item removed from stock")
        return redirect(url_for("store"))
    flash("hey you're not admin stop that")
    return redirect(url_for("store"))

@app.route("/cart")
def getCart():
    #creates a query that returns every item in the sessions basket
    q = {"_id" : {"$in" : [ObjectId(id) for id in session["basket"]]}}
    basket = list(mongo.db.stock.find(q))
    cost = sum(float(item["cost"]) for item in basket)
    balance = get_balance(session["user"])
    return render_template("basket.html", basket=basket, totalCost=cost, balance=balance)

@app.route("/sendPurchase")
def purchaseAll():    
    q = {"_id": {"$in": [ObjectId(id) for id in session["basket"]]}}
    basket = list(mongo.db.stock.find(q))
    cost = sum(float(item["cost"]) for item in basket)
    if cost <= get_balance(session["user"]): 
        bought = {"$set": {"boughtBy": session["user"], "sold": True}}
        mongo.db.stock.update_many(q, bought)
        session["basket"] = []
        update_balance(session["user"], -cost)
        flash("items bought")

    
    return render_template("home.html")

def get_balance(username):
    user =  mongo.db.users.find_one({"username": username}, {"balance":1})
    return user.get("balance", 0)

def update_balance(username, change):
    print("hi")
    user = mongo.db.users.find_one({"username": username}, {"balance":1})
    print(user)
    curr_balance = user.get("balance", 0)
    new_balance = curr_balance + change 
    print(new_balance)
    mongo.db.users.update_one({"username": username}, {"$set": {"balance": new_balance}})
    

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
