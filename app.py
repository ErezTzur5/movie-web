import base64
import re
from base64 import b64encode
from flask import Flask, render_template, request, redirect, session ,url_for
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from flask import request, session
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from datetime import datetime
from sqlalchemy import LargeBinary


from PIL import Image

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies_site_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "abcdf"

db = SQLAlchemy(app)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now())
    rate = db.Column(db.Integer)

    movie = db.relationship('Movie', backref=db.backref('comments', lazy=True))
    user = db.relationship('User', backref=db.backref('comments', lazy=True))


class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    image = db.Column(LargeBinary)
    description = db.Column(db.Text)
    director = db.Column(db.String(100))
    actors = db.Column(db.String(200))
    release_year = db.Column(db.Integer)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(50))


# Check if tables exist and create them if they don't
def create_tables():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('movies'):
            db.create_all()
        if not inspector.has_table('users'):
            db.create_all()
        if not inspector.has_table('comments'):
            db.create_all()
        if not inspector.has_table('ratings'):
            db.create_all()

# Call the create_tables() function to create tables if they don't exist
# create_tables()



@app.route('/')
def home(): 
    """
    this is the homepage of the web,
    homepage is represent all the movies that in database
    if you click them you will go into the movie page
    its also check for user id and if the user role is admin 
    for special actions like post or delete movies.
    (for posting movie need to click on the menu top right)

    """
    admin = False
    user_id = session.get('user_id')
    movies = Movie.query.all()
    if not user_id:
        if movies:
            for movie in movies:
                if movie.image:
                    encoded_image = base64.b64encode(movie.image).decode('utf-8')
                    movie.image = encoded_image
            return render_template('index.html', movies=movies)

    if user_id:
        user = User.query.get(user_id)
        if user:
            username = user.username
            role = user.role
            if role == 'admin':
                admin = True

            for movie in movies:
                if movie.image:
                    encoded_image = base64.b64encode(movie.image).decode('utf-8')
                    movie.image = encoded_image
            return render_template('index.html', username=username, admin=admin, movies=movies)
    
    return render_template('index.html', movies=movies)


def login_required(f): 
    """
    Checking the user id in the session.
    Incase the user is not logged in it will redirect to login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f): #checking the user role , if user role is admin then he will have special premission , like post or delete movies
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        user = User.query.filter_by(id=user_id).first()
        if not user or user.role != 'admin':
            return redirect(url_for('home'))

        return f(*args, **kwargs)

    return decorated_function

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def post_movie():
    """
    This is an posting movie page that only admin role user can reach
    in the page we need to fill all the required data:
    title, description, director, actors, release_year and image.
    the image we upload will be saved in the database using SQLAlchemy as binary type
    """
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            username = user.username
            if request.method == 'POST':
                # Get the form data
                title = request.form['title']
                description = request.form['description']
                director = request.form['director']
                actors = request.form['actors']
                release_year = request.form['release_year']

                # Handle the image file upload
                image = request.files['image']
                image_data = image.read()  # Read the image file as binary data

                # Create a new Movie object
                movie = Movie(
                    title=title,
                    image=image_data,
                    description=description,
                    director=director,
                    actors=actors,
                    release_year=release_year
                )

                # Add the movie to the database
                db.session.add(movie)
                db.session.commit()

                return redirect('/')

        return render_template('admin.html', username=username)

    return redirect(url_for('login'))

@app.route('/movie', methods=['GET', 'POST'])
def movie_page():
    """
    Creating a dynamic movie page per movie.
    This movie page will represent all the data for the movie (in the post movie above) and will show it in style way.
    Users can also star-rate and comment on the movie and it will represent too. 
    The rating and the comments will be saved in database table.
    """
    movie_name = request.args.get('name')

    movie = Movie.query.filter_by(title=movie_name).first()
    print('hello',movie.id)
    if movie:
        # print("Found movie:",movie.id, movie.title, movie.image, movie.description, movie.director, movie.actors, movie.release_year)
        user_id = session.get('user_id')

        if user_id:
            user = User.query.get(user_id)
            username = user.username

            if request.method == 'POST':
                comment_content = request.form.get('comment')
                rating_value = request.form.get('star-input')


                # Save the comment
                comment = Comment(movie=movie, user=user, content=comment_content,created_at=datetime.now(),rate=rating_value)
                db.session.add(comment)

                db.session.commit()

            comments = Comment.query.filter_by(movie_id=movie.id).all()
            movie_image = b64encode(movie.image).decode('utf-8')
            return render_template('movie_details.html', username=username, user_id=user_id, title=movie.title,
                                   movie_image=movie_image, description=movie.description,
                                   director=movie.director, actors=movie.actors, release_year=movie.release_year,
                                   comments=comments)
        else:
            return render_template('login.html')

    return render_template('not_found.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    This is the Signup page , upon creating an account it will automatic role the user as regular and not admin.
    for the password requirements is atleast 8 characters and atleast 1 character must be capital letter.
    for the username requirements is atleast 4 characters.
    If the user doesnt meet the requirements it will tell you exacly what to change.
    This also checks if the user already exist and if so it will tell you .
    """
    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        password = request.form['password']
        if 'role' in request.form:
            role = request.form['role']
        else:
            role = 'regular'

        # Validate password requirements
        if len(password) <= 8 or not any(char.isupper() for char in password):
            return render_template('signup.html', error=True, password_error=True)

        # Validate username requirements
        if len(username) <= 4:
            return render_template('signup.html', error=True, username_error=True)

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('signup.html', error=True, username_taken=True)

        # Create a new User object
        user = User(
            username=username,
            password=password,
            role=role
        )

        # Add the user to the database
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect('/')

    return render_template('signup.html', error=False)



@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page for users to login to the web
    so they can see the movies, rate and comment.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database for the user
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            return redirect('/')
        else:
            return "Invalid username or password"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/delete/<int:movie_id>', methods=['POST'])
@login_required
@admin_required
def delete_movie(movie_id):
    """
    As the Decorator mention above, This function is only available for admin role, so he can delete the movie if needs.
    
    """
    movie = Movie.query.get(movie_id)

    if movie:
        # Delete the associated comments
        Comment.query.filter_by(movie_id=movie.id).delete()

        db.session.delete(movie)
        db.session.commit()

    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
