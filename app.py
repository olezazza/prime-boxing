import os
from flask import Flask, render_template, url_for, flash, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'prime_boxing_secret_key_change_this_later'

# --- DATABASE CONNECTION LOGIC ---
# Check if we are on Render (they provide DATABASE_URL)
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Fix Render's URL (Postgres requires 'postgresql://', Render gives 'postgres://')
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # We are on Localhost -> Use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(50), nullable=False)  # Increased length for "Monday - Saturday"
    day_order = db.Column(db.Integer, nullable=False)
    time = db.Column(db.String(20), nullable=False)
    class_name = db.Column(db.String(100), nullable=False)
    coach = db.Column(db.String(100), nullable=False)

class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    features = db.Column(db.Text, nullable=False)
    is_featured = db.Column(db.Boolean, default=False)

class Coach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(500), nullable=False)

# --- FORMS ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class WorkoutForm(FlaskForm):
    # UPDATED: Added generic options (0 and 8)
    day = SelectField('Day', choices=[
        ('0', 'MONDAY - SATURDAY'),
        ('8', 'MONDAY - FRIDAY'),
        ('1', 'MONDAY'), ('2', 'TUESDAY'), ('3', 'WEDNESDAY'),
        ('4', 'THURSDAY'), ('5', 'FRIDAY'), ('6', 'SATURDAY'), ('7', 'SUNDAY')
    ])
    time = StringField('Time (e.g. 19:00)', validators=[DataRequired()])
    class_name = StringField('Class Name', validators=[DataRequired()])
    coach = StringField('Coach Name', validators=[DataRequired()])
    submit = SubmitField('Save Class')

class PriceForm(FlaskForm):
    title = StringField('Plan Title', validators=[DataRequired()])
    cost = StringField('Cost (e.g. 150 GEL)', validators=[DataRequired()])
    frequency = StringField('Frequency (e.g. / Month)', validators=[DataRequired()])
    features = TextAreaField('Features (comma separated)', validators=[DataRequired()])
    is_featured = SelectField('Highlight?', choices=[('0', 'No'), ('1', 'Yes')])
    submit = SubmitField('Save Plan')

class CoachForm(FlaskForm):
    name = StringField('Coach Name', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    photo_url = StringField('Photo URL (Use Unsplash or leave blank)', validators=[DataRequired()])
    submit = SubmitField('Save Coach')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---
@app.route("/")
def home():
    return render_template('home.html')

@app.route("/schedule")
def schedule():
    workouts = Workout.query.order_by(Workout.day_order, Workout.time).all()
    return render_template('schedule.html', workouts=workouts)

@app.route("/prices")
def prices():
    plans = Price.query.all()
    return render_template('prices.html', plans=plans)

@app.route("/gallery")
def gallery():
    coaches = Coach.query.all()
    return render_template('gallery.html', coaches=coaches)

# --- ADMIN ROUTES ---
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

# WORKOUT ADMIN
@app.route("/admin/workout/new", methods=['GET', 'POST'])
@login_required
def create_workout():
    form = WorkoutForm()
    if form.validate_on_submit():
        # UPDATED: Maps the numbers to text
        days_map = {
            '0': 'MONDAY - SATURDAY',
            '8': 'MONDAY - FRIDAY',
            '1': 'MONDAY', '2': 'TUESDAY', '3': 'WEDNESDAY',
            '4': 'THURSDAY', '5': 'FRIDAY', '6': 'SATURDAY', '7': 'SUNDAY'
        }
        
        workout = Workout(
            day=days_map[form.day.data], 
            day_order=int(form.day.data), 
            time=form.time.data, 
            class_name=form.class_name.data, 
            coach=form.coach.data
        )
        db.session.add(workout)
        db.session.commit()
        return redirect(url_for('schedule'))
    return render_template('create_content.html', form=form, title="ADD CLASS")

@app.route("/admin/workout/delete/<int:id>")
@login_required
def delete_workout(id):
    db.session.delete(Workout.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('schedule'))

# PRICE ADMIN
@app.route("/admin/price/new", methods=['GET', 'POST'])
@login_required
def create_price():
    form = PriceForm()
    if form.validate_on_submit():
        plan = Price(title=form.title.data, cost=form.cost.data, frequency=form.frequency.data, features=form.features.data, is_featured=(form.is_featured.data == '1'))
        db.session.add(plan)
        db.session.commit()
        return redirect(url_for('prices'))
    return render_template('create_content.html', form=form, title="ADD PRICE")

@app.route("/admin/price/delete/<int:id>")
@login_required
def delete_price(id):
    db.session.delete(Price.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('prices'))

# COACH ADMIN
@app.route("/admin/coach/new", methods=['GET', 'POST'])
@login_required
def create_coach():
    form = CoachForm()
    if form.validate_on_submit():
        coach = Coach(name=form.name.data, title=form.title.data, photo_url=form.photo_url.data)
        db.session.add(coach)
        db.session.commit()
        return redirect(url_for('gallery'))
    return render_template('create_content.html', form=form, title="ADD COACH")

@app.route("/admin/coach/delete/<int:id>")
@login_required
def delete_coach(id):
    db.session.delete(Coach.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('gallery'))

# --- DATABASE CREATION (Runs on Deploy) ---
with app.app_context():
    # Safe Create: Only creates tables if they don't exist
    db.create_all()
    
    # Initial Admin Setup (Only runs once)
    if not User.query.first():
        admin = User(username="admin", password=generate_password_hash("admin123"))
        db.session.add(admin)
        
        # NOTE: Dummy data removed so you can add real data manually
        
        db.session.commit()
        print("Database initialized.")

if __name__ == '__main__':
    app.run(debug=True)
