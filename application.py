import os
import re
import requests
from datetime import datetime

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import and_, or_, func
from models import *

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


class ReviewCl:
    def __init__(self, review, rating, login, review_date):
        self.review = review
        self.rating = rating
        self.login = login
        self.review_date = review_date


@app.route("/", methods=['GET'])
def index():
    if session.get('login') is None:
        return redirect(url_for("login"))
    login = session['login']
    books = Books.query.order_by(Books.year.desc()).limit(20).all()
    return render_template("index.html", books=books, login=login.capitalize())


@app.route("/search", methods=['GET'])
def search():
    if session.get('login') is None:
        return redirect(url_for("login"))
    login = session['login'].capitalize()
    text = request.args.get("book_search").lower()
    if text != '':
        books = Books.query.filter(or_(Books.authors.has(func.lower(Authors.author_name).like(f'%{text}%')),
                                       func.lower(Books.title).like(f'%{text}%'),
                                       func.lower(Books.isbn).like(f'%{text}%')))
    return render_template("index.html", books=books, login=login, back=True)


@app.route("/book_details/<int:book_id>", methods=['GET'])
def book_details(book_id):
    if session.get('login') is None:
        return redirect(url_for("login"))
    user_id = Users.query.filter_by(login=session['login']).first().id
    is_reviewable = not Reviews.query.filter_by(book_id=book_id, user_id=user_id).count() > 0
    book = Books.query.get(book_id)
    if book is None:
        return '404'
    author = Authors.query.get(book.author_id)
    reviews = Reviews.query.filter_by(book_id=book_id).all()
    try:
        goodreads_rating = requests.get(os.getenv("GOODREADS_RATING_COUNTS_URL"), params={"key":os.getenv("GOODREADS_API_KEY"), "isbns": book.isbn}).json()
    except Exception as e:
        goodreads_rating = None
    return render_template("book.html", book=book, author=author, reviews=reviews, is_reviewable=is_reviewable, goodreads_rating=goodreads_rating)


@app.route("/submit_review", methods=['POST'])
def submit_review():
    if session.get('login') is None:
        return redirect(url_for("login"))
    user_id = Users.query.filter_by(login=session['login']).first().id
    book_id = request.form.get("book_id")
    rating = request.form.get("book_rating")
    review_text = request.form.get("review_text")
    review = Reviews(user_id=user_id, book_id=book_id, rating=rating, review=review_text, review_date=datetime.now())
    db.session.add(review)
    db.session.commit()
    return redirect(url_for(f"book_details", book_id=book_id))


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get("login")
        password = request.form.get("password")
        user = Users.query.filter_by(login=login).first()
        if user is None:
            return 'Incorrect login or password'
        if password != user.password:
            return 'Incorrect login or password'
        session['login'] = login
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        login = request.form.get("login")
        email = request.form.get("email")
        password = request.form.get("password")
        if not re.match("\w+@{1}\w+\.{1}\w+", email):
            return 'Incorrect email'
        login_check = Users.query.filter_by(login=login).first()
        email_check = Users.query.filter_by(email=email).first()
        if login_check is not None or email_check is not None:
            return 'User with such login or email already exists'
        user = Users(login=login, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/logout")
def logout():
    if session['login'] is not None:
        session['login'] = None
    return redirect(url_for("login"))


@app.route("/api/<string:isbn>")
def api(isbn):
    result = dict()
    if session.get('login') is None:
        return redirect(url_for("login"))
    book = Books.query.filter_by(isbn=isbn).first()
    try:
        goodreads_rating = requests.get(os.getenv("GOODREADS_RATING_COUNTS_URL"), params={"key":os.getenv("GOODREADS_API_KEY"), "isbns": book.isbn}).json()
    except Exception as e:
        goodreads_rating = None
    result["title"] = book.title
    result["author"] = book.authors.author_name
    result["year"] = book.year
    result["isbn"] = book.isbn
    if goodreads_rating is not None:
        result["review_count"] = goodreads_rating["books"][0]['ratings_count']
        result["average_score"] = float(goodreads_rating["books"][0]['average_rating'])
    return jsonify(result)

