import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash
from firebase_admin import firestore
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase
cred = credentials.Certificate(r'D:\Projects\JobPortal\firebase_credentials.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

app = Flask(__name__)

# Configuration
app.secret_key = 'your_secret_key'  # This should be a secure key
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect to login page if not logged in
app.config['UPLOAD_FOLDER'] = 'static/images/uploads'  # Directory for storing uploaded images
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check if the file is an allowed type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Initialize the Login Manager to manage session data
login_manager.session_protection = "strong"

# User class for Flask-Login compatibility
class User(UserMixin):
    def __init__(self, user_id, email, name=None):
        self.id = user_id
        self.email = email
        self.name = name  # Add name to store user's name

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    try:
        user = auth.get_user(user_id)
        return User(user_id=user.uid, email=user.email, name=user.display_name)  # Fetch display_name (name)
    except firebase_admin.exceptions.FirebaseError:
        return None

# Function to add a user
def add_user(email, password, name):
    try:
        # Add user to Firebase Authentication
        user = auth.create_user(
            email=email,
            password=password,
            display_name=name  # Set the user's name
        )
        
        # Store user details in Firestore
        user_ref = db.collection('users').document(user.uid)  # Reference to the Firestore document
        user_ref.set({
            'email': email,
            'name': name  # Save the name explicitly in Firestore
        })

        print(f"Successfully created user: {user.uid}")
        return user
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

@app.route('/')
def home():
    if current_user.is_authenticated:
        # Fetch jobs only for logged-in users
        jobs = db.collection('jobs').stream()  # Example Firestore query
        job_list = [
            {
                'title': job.get('title'),
                'company': job.get('company'),
                'location': job.get('location'),
                'salary': job.get('salary'),
                'description': job.get('description'),
                'thumbnail': job.get('thumbnail'),
                'application_link': job.get('application_link')
            }
            for job in jobs
        ]
    else:
        job_list = []  # No jobs for non-logged-in users

    return render_template('home.html', jobs=job_list, is_home_page=True)

@app.route('/add-job', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        # Get job details from the form
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        company = request.form['company']
        salary = request.form['salary']
        job_type = request.form['job_type']
        eligibility = request.form['eligibility']
        application_link = request.form['application_link']

        # Handle the thumbnail upload
        thumbnail = request.files['thumbnail']
        thumbnail_filename = None

        if thumbnail and allowed_file(thumbnail.filename):
            # Secure the filename and save it to the uploads folder
            thumbnail_filename = secure_filename(thumbnail.filename)
            thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))

        # Prepare data to store in Firestore
        job_data = {
            'title': title,
            'description': description,
            'location': location,
            'company': company,
            'salary': salary,
            'job_type': job_type,
            'eligibility': eligibility,
            'application_link': application_link,
            'thumbnail': thumbnail_filename  # Save the thumbnail filename in the job data
        }

        # Add job to Firestore
        try:
            jobs_ref = db.collection('jobs')  # 'jobs' collection in Firestore
            jobs_ref.add(job_data)
            flash('Job posted successfully!', 'success')
            return redirect(url_for('job_list'))  # Redirect to the job listing page
        except Exception as e:
            flash(f"Error posting job: {str(e)}", 'danger')

    return render_template('add_job.html')  # Render the job posting form

@app.route('/jobs')
def job_list():
    # Get all job listings from Firestore
    jobs = db.collection('jobs').stream()
    
    job_list = [
        {
            'title': job.get('title'),
            'company': job.get('company'),
            'location': job.get('location'),
            'salary': job.get('salary'),
            'description': job.get('description'),
            'thumbnail': job.get('thumbnail'),
            'application_link': job.get('application_link')
        }
        for job in jobs
    ]
    
    return render_template('job_list.html', jobs=job_list)

@app.route('/add-user', methods=['GET', 'POST'])
def add_user_route():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']

        new_user = add_user(email, password, name)

        if new_user:
            flash(f"User {name} added successfully!", 'success')
        else:
            flash("Failed to add user. Please try again.", 'danger')

    return render_template('add_user.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login requests."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        try:
            user = auth.get_user_by_email(username)
            login_user(User(user_id=user.uid, email=user.email, name=user.display_name))  # Pass display_name (name)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))  # Redirect to jobs after login
        except firebase_admin.exceptions.FirebaseError:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
