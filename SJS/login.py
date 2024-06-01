"dont look this"

from flask import Flask, render_template, request, redirect, session, url_for, flash
from pymongo import MongoClient
import bcrypt

app = Flask(__name__, template_folder='../templates')
app.secret_key = "lawgpt@1234" 

# Connect to MongoDB
client = MongoClient('mongodb+srv://saipraneethkambhampati800:PFTyvSKltwa4wBFB@cluster0.w2azzd2.mongodb.net/')
db = client['SJS']
users_collection = db['users']
lawyers_collection = db['lawyers']

@app.route('/')
@app.route('/home')
def home():
    if 'number' in session:
        user_data = None
        role = None
        if users_collection.find_one({'number': session['number']}):
            user_data = users_collection.find_one({'number': session['number']})
            role = 'user'
        elif lawyers_collection.find_one({'number': session['number']}):
            user_data = lawyers_collection.find_one({'number': session['number']})
            role = 'lawyer'

        if user_data:
            if role == 'lawyer':
                return redirect(url_for('lawyer_home'))
            elif role == 'user':
                return redirect(url_for('user_home'))
    
    return render_template('index.html')

@app.route('/user_home')
def user_home():
    if 'number' in session:
        return "user home"
    else:
        return render_template('index.html')

@app.route('/lawyer_home')
def lawyer_home():
    if 'number' in session:
        return "lawyer home"
    
    else:
        return render_template('index.html')
    


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session:
        redirect(url_for('/home'))

    if request.method == 'POST':
        existing_user = users_collection.find_one({'number': request.form['number']})
        existing_lawyer = lawyers_collection.find_one({'number': request.form['number']})

        if existing_user is None and existing_lawyer is None:
            hashed_password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            user_data = {
                'username': request.form['username'],
                'aadharnumber': request.form['aadharnumber'],
                'email': request.form['email'],
                'password': hashed_password,
                'role': request.form['role']
            }
            if request.form['role'] == 'lawyer':
                lawyers_collection.insert_one(user_data)
            else:
                users_collection.insert_one(user_data)    
            flash("Registration Successful, please login using your details")
            return render_template('login.html')
        else:
            flash("That phone number is already registered!")
            return render_template('register.html')
    
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if session:
        redirect(url_for('home'))
    
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = request.form['password']

        if role == 'lawyer':
            existing_user = lawyers_collection.find_one({'username': username})
        else:
            existing_user = users_collection.find_one({'username': username})

        if existing_user:
            if bcrypt.checkpw(password.encode('utf-8'), existing_user['password']):
                session['aadharnumber'] = username
                return redirect(url_for('home'))
            else:
                flash('Invalid aadhar number/password combination')
        else:
            flash('Invalid aadhar number/password combination')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
