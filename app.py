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
        flash("registration successful")
        return redirect(url_for("get_home"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        print("hi")
        logout()

    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        existing = mongo.db.users.find_one({"username": username})
        print(existing)
        print(password)
        print(generate_password_hash(password))
        if existing and check_password_hash(existing.get("password", None), password):
            print("hi")
            session["user"] = username
            flash(f'logged in as {username}')
            return redirect(url_for("get_home"))
        
        flash("incorrect username or pasword")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged Out")
    return redirect(url_for("get_home"))

@app.route("/user/<username>")
def get_user(username):

    #name
    #id
    #delete account
    user = mongo.db.users.find_one({"username": session["user"]})

    

    logged_in = (username == session.get("user", None)) #only show basket info, delete account etc if true


    #view basket 
    return render_template("user.html", user=user, logged_in=logged_in)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
