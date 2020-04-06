import os
from csv import reader

from flask import Flask

# Import table definitions.
from models import *

app = Flask(__name__)

# Tell Flask what SQLAlchemy databas to use.
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Link the Flask app with the database (no Flask app is actually being run yet).
db.init_app(app)


def main():
    # Create tables based on each table definition in `models`
    authors = set()
    books = []
    with open("./books.csv", 'r') as f:
        for i, line in enumerate(reader(f)):
            if i == 0:
                continue
            authors.add(line[2])
            books.append(line)
    for author in authors:
        a = Authors(author_name=author)
        db.session.add(a)
        db.session.commit()
    for book in books:
        author = Authors.query.filter_by(author_name=book[2]).first()
        b = Books(isbn=book[0], title=book[1], author_id=author.id, year=int(book[3]))
        db.session.add(b)
        db.session.commit()


if __name__ == "__main__":
    # Allows for command line interaction with Flask application
    with app.app_context():
        main()