from flask import Flask, redirect, url_for, render_template, abort, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextField, SelectField
from wtforms.validators import DataRequired, Email
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import smtplib
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from functions import find_place_id, send_email

GMAIL_ACCOUNT = os.environ.get("GMAIL_ACCOUNT")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
app = Flask(__name__)
Bootstrap(app)
year = datetime.now().year

# Creating the shops database
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///pret_shops.db"
app.config['SECRET_KEY'] = os.environ.get("SQLALCHEMYAPPKEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))


class Shops(db.Model):
    __tablename__ = "shops"
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(250), unique=True, nullable=False)
    shop_address = db.Column(db.String(250), unique=False, nullable=False)


# db.create_all()
#
# # Scrape the Pret London Locations
#
# response = requests.get("https://locations.pret.co.uk/london")
# response.raise_for_status()
# data = response.text
# soup = BeautifulSoup(data, "html.parser")
# shops = soup.find_all("a", class_="Teaser-titleLink")
# shop_names = [shop.text for shop in shops]
# addresses = soup.find_all("div", class_="Teaser-address")
# shop_addresses = [address.text for address in addresses]
#
# # Populate the database with the shop names and addresses
# for shop, address in zip(shop_names, shop_addresses):
#     try:
#         new_shop = Shops(shop_name=shop, shop_address=address)
#         db.session.add(new_shop)
#         db.session.commit()
#     except exc.SQLAlchemyError:
#         db.session.rollback()


@app.route("/")
@app.route("/index")
def home():
    return render_template("index.html", year=year)


@app.route("/reviews")
def review_checker():
    all_shops = Shops.query.order_by("shop_name").all()
    return render_template("reviews.html", year=year, shops=all_shops)


@app.route("/<shop_review>")
def show_review(shop_review):

    place_id = find_place_id(shop=shop_review)

    # Send an API details request for shop reviews and address by supplying the ID
    reviews_params = {
        "key": GOOGLE_API_KEY,
        "place_id": place_id,
        "fields": "review,rating,formatted_address"
    }
    google_review_response = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=reviews_params)
    google_review_response.raise_for_status()
    # print (google_review_response.json())

    # An exception handling in case of latency from the Google Server
    try:
        reviews = google_review_response.json()["result"]["reviews"]
        rating = google_review_response.json()["result"]["rating"]
        address = google_review_response.json()["result"]["formatted_address"]
    except KeyError:
        abort(404)
    else:
        return render_template("review-details.html", shop=shop_review, address=address, rating=rating, reviews=reviews, year=year)


@app.route("/location")
def location_checker():

    # Return all shops in the database
    all_shops = Shops.query.order_by("shop_name").all()
    return render_template("locations.html", year=year, shops=all_shops)


@app.route("/<shop>/<address>")
def location_review(shop, address):

    # Send an API request for a static map
    map_params = {
        "key": GOOGLE_API_KEY,
        "size": "800x400",
        "scale": 1,
        "markers": f"{address}",
        "zoom": 15
    }
    google_map_response = requests.get(f"https://maps.googleapis.com/maps/api/staticmap", params=map_params)
    google_map_response.raise_for_status()
    map_img = google_map_response.url

    place_id = find_place_id(shop=shop)

    # Send an API request for opening times and phone number
    reviews_params = {
        "key": GOOGLE_API_KEY,
        "place_id": place_id,
        "fields": "formatted_phone_number,opening_hours"
    }
    google_review_response = requests.get("https://maps.googleapis.com/maps/api/place/details/json",
                                          params=reviews_params)
    google_review_response.raise_for_status()

    # An exception handling in case of latency from the Google Server
    try:
        phone_number = google_review_response.json()["result"]["formatted_phone_number"]
        opening_times = google_review_response.json()["result"]["opening_hours"]["weekday_text"]
    except KeyError:
        abort(404)
    else:
        return render_template("location-details.html", shop=shop, address=address, year=year, map=map_img, phone=phone_number, days=opening_times)


# @app.route("/labor")
# def calculate_labor():
#     return render_template("calculator.html")

@app.route("/sub", methods=["POST", "GET"])
def newsletter_sub():

    # Send an email to subscribers
    if request.method == "POST":
        recipient = request.form["email"]
        message = f"Subject:Welcome to the Neswletter\n\nThank you for taking the time to register for our Newsletter.\n" \
                  f"We will be sending out a recap of any new features and updates to existing ones from time to time 😉."
        send_email(recipient, message.encode("utf8"))

        return redirect(url_for("home"))


@app.route("/message", methods=["POST", "GET"])
def send_message():

    # Send myself the message users are submitting
    if request.method == "POST":
        recipient = GMAIL_ACCOUNT
        message = f"Subject:{request.form['subject']}\n\n{request.form['name']} sent a message:\n{request.form['message']}.\n"\
                  f"Send reply to {request.form['email']}."
        send_email(recipient, message.encode("utf8"))
        flash("Message Successfully Sent! Thank you!")
        return redirect(url_for("home", _anchor="footer"))
    return redirect(url_for("home"))


# @app.route('/register', methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#
#         if User.query.filter_by(email=request.form["email"]).first():
#
#             #User already exists
#             flash("You've already signed up with that email, log in instead!")
#             return redirect(url_for('login'))
#
#         hash_and_salted_password = generate_password_hash(
#             request.form["password"],
#             method='pbkdf2:sha256',
#             salt_length=8
#         )
#         new_user = User(
#             email=request.form["email"],
#             name=request.form["name"],
#             password=hash_and_salted_password,
#         )
#         db.session.add(new_user)
#         db.session.commit()
#         login_user(new_user)
#         return redirect(url_for("home"))
#
#     return render_template("register.html", current_user=current_user)
#
#
# @app.route('/login', methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         email = request.form["email"]
#         password = request.form["password"]
#
#         user = User.query.filter_by(email=email).first()
#         # Email doesn't exist or password incorrect.
#         if not user:
#             flash("That email does not exist, please try again.")
#             return redirect(url_for('login'))
#         elif not check_password_hash(user.password, password):
#             flash('Password incorrect, please try again.')
#             return redirect(url_for('login'))
#         else:
#             login_user(user)
#             return redirect(url_for('home'))
#     return render_template("login.html", current_user=current_user)


if __name__ == "__main__":
    app.run()
