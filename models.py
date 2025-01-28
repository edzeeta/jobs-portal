from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Database URI
app.config['SECRET_KEY'] = 'your_secret_key'  # Set your secret key

# Initialize the database
db = SQLAlchemy(app)

# Define the Student model
class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
