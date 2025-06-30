from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
project_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(project_dir, "rentals.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'owner', 'buyer', 'admin'

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    rent = db.Column(db.String(20))
    contact = db.Column(db.String(100))
    posted_by = db.Column(db.String(100))  # username of the owner

# Create tables and default admin
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='admin123', role='admin')
        db.session.add(admin_user)
        db.session.commit()

# Routes
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        user = User.query.filter_by(username=username, password=password, role=role).first()
        if user:
            session['username'] = user.username
            session['role'] = user.role
            return redirect('/dashboard')
        else:
            error = "Invalid login. Try again."
    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if role == 'admin':
            error = "Cannot create admin account."
        elif User.query.filter_by(username=username).first():
            error = "Username already exists."
        else:
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')
    return render_template('signup.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect('/')
    if session['role'] == 'owner':
        return redirect('/owner')
    elif session['role'] == 'buyer':
        return redirect('/listings')
    elif session['role'] == 'admin':
        return redirect('/admin')
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/owner')
def owner_form():
    if session.get('role') != 'owner':
        return redirect('/')
    posted = request.args.get('posted') == 'true'
    owner_username = session.get('username')
    listings = Listing.query.filter_by(posted_by=owner_username).all()
    return render_template('index.html', posted=posted, listings=listings)

@app.route('/post', methods=['POST'])
def post():
    if session.get('role') != 'owner':
        return redirect('/')
    new_listing = Listing(
        name=request.form['name'],
        address=request.form['address'],
        rent=request.form['rent'],
        contact=request.form['contact'],
        posted_by=session.get('username')
    )
    db.session.add(new_listing)
    db.session.commit()
    return redirect('/owner?posted=true')

@app.route('/listings')
def show_listings():
    query = request.args.get('q', '')
    if query:
        listings = Listing.query.filter(
            (Listing.name.ilike(f'%{query}%')) |
            (Listing.address.ilike(f'%{query}%'))
        ).all()
    else:
        listings = Listing.query.all()
    return render_template('listings.html', listings=listings)

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        return redirect('/')
    users = User.query.all()
    listings = Listing.query.all()
    listings_by_owner = {}
    for listing in listings:
        listings_by_owner.setdefault(listing.posted_by, []).append(listing)
    return render_template('admin.html', users=users, listings_by_owner=listings_by_owner)

@app.route('/admin/edit/<int:listing_id>', methods=['GET', 'POST'])
def admin_edit_listing(listing_id):
    if session.get('role') != 'admin':
        return redirect('/')
    listing = Listing.query.get_or_404(listing_id)
    if request.method == 'POST':
        listing.name = request.form['name']
        listing.address = request.form['address']
        listing.rent = request.form['rent']
        listing.contact = request.form['contact']
        db.session.commit()
        return redirect('/admin')
    return render_template('edit_listing.html', listing=listing)

@app.route('/admin/delete/<int:listing_id>')
def admin_delete_listing(listing_id):
    if session.get('role') != 'admin':
        return redirect('/')
    listing = Listing.query.get_or_404(listing_id)
    db.session.delete(listing)
    db.session.commit()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
