from flask import Flask # type: ignore
import os
from flask import Blueprint, jsonify, make_response, redirect, render_template, request, session, url_for, flash # type: ignore
import openai
import confidential as keys
import boto3
from pymongo import MongoClient
import bcrypt # type: ignore
from werkzeug.utils import secure_filename # type: ignore
# from google.cloud import speech_v1p1beta1 as speech
# import io

s3 = boto3.client('s3',
                    aws_access_key_id=keys.ACCESS_KEY_ID,
                    aws_secret_access_key= keys.ACCESS_SECRET_KEY
                 )

BUCKET_NAME= keys.BUCKET_NAME

app = Flask(__name__)
app.secret_key = 'lawyer@1234'
app.static_folder = "static"

# Connect to MongoDB
client = MongoClient('mongodb+srv://saipraneethkambhampati800:PFTyvSKltwa4wBFB@cluster0.w2azzd2.mongodb.net/')
db = client['SJS']
users_collection = db['users']
lawyers_collection = db['lawyers']

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    if 'aadharnumber'  in session:
        if session['role'] == 'lawyer':
            return redirect(url_for('dashboard'))
        elif session['role'] == 'user' :
            return redirect(url_for('user_home'))
    session.clear()
    return render_template('indexMain.html')

@app.route('/user_home')
def user_home():
    if 'aadharnumber' in session:
        return redirect(url_for('chatbot'))
    else:
        return render_template('indexMain.html')

@app.route('/login',methods=['GET', 'POST'])
def login():
    if 'aadharnumber' in session:
        redirect(url_for('home'))
    
    if request.method == 'POST':
        
        role = request.form['role']
        username = request.form['aadharnumber']
        password = request.form['password']

        if role == 'lawyer':
            existing_user = lawyers_collection.find_one({'aadharnumber': str(username)})
        else:
            existing_user = users_collection.find_one({'aadharnumber': str(username)})
        if existing_user:
            if bcrypt.checkpw(password.encode('utf-8'), existing_user['password']):
                session['aadharnumber'] = existing_user['aadharnumber']
                session['role'] = existing_user['role']
                return redirect(url_for('home'))
            else:
               return render_template('login.html', message = "Password Incorrect")
        else:
           return render_template('login.html', message = "Login Failed/ Invalid Aadhar Number")
    session.clear()
    return render_template('login.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')


if __name__ == '__main__':
    app.run(debug=True)


@app.route('/register',methods=['GET', 'POST'])
def register():
    if 'aadharnumber' in session:
        redirect(url_for('home'))
    if request.method == 'POST':
        existing_user = users_collection.find_one({'aadharnumber': request.form['aadharnumber']})
        existing_lawyer = lawyers_collection.find_one({'aadharnumber': request.form['aadharnumber']})
        if existing_user is None and existing_lawyer is None:
            hashed_password = bcrypt.hashpw(request.form['password'].encode('utf-8'),bcrypt.gensalt())
            user_data = {
                'name': request.form['name'],
                'aadharnumber': request.form['aadharnumber'],
                'email': request.form['email'],
                'password': hashed_password,
                'role': request.form['role'],
                'docs' : [], 
                'tasks' : []
            }
            if request.form['role'] == 'lawyer':
                lawyers_collection.insert_one(user_data)
                smsg  = 'lawyer succesfully registered'
            else:
                users_collection.insert_one(user_data)    
                smsg  = ' user succesfully registered'

            return render_template('login.html', smsg = smsg )
        else:
            return render_template('register.html', message = "User Already Exists!!")
    return render_template('register.html', message = "Not Sucessfully Registered/ Try Again with Correct Inputs")


@app.route('/dashboard')
def dashboard():
    if 'aadharnumber' in session:
        aadharnumber = str(session['aadharnumber'])
        query = {'aadharnumber':aadharnumber}
           
        law_data = lawyers_collection.find_one(query, {'_id':0})
    
        print(law_data['docs'])
        return render_template('dashboard.html', data = law_data)        
    return redirect(url_for('home'))


@app.route('/chatbot')
def chatbot():
    if "aadharnumber" in session:
        if session['role'] == "lawyer":
            return redirect("http://localhost:8501", code=302)
        elif session['role'] == "user":
            return redirect("http://localhost:8502", code=302)
        else:
            return render_template('chatbot.html')
    return redirect(url_for('login'))


@app.route('/upload_file',methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        img = request.files['file']
        if img:
                filename = secure_filename(img.filename)
                img.save(filename)
                s3.upload_file(
                    Bucket = BUCKET_NAME,
                    Filename=filename,
                    Key = filename
                )
                msg = "Upload Done !"
                return render_template('upload_file.html', msg=msg) 
        
    return render_template('upload_file.html')



@app.route('/get_bot')
def get_bot():

    user_text = request.args.get('msg')
    openai.api_key = keys.OPEN_AI_KEY
    prompt = f"I'm here to help you understand complex legal topics. Please provide a prompt or question about Indian laws, and I'll provide you with a clear and concise summary. What would you like to know about? Your prompt or question: {user_text}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.5,
        max_tokens = 200
    )
    generated_response = response['choices'][0]['message']['content']
    return generated_response
    

# Documents Route


@app.route('/my_documents', methods =['GET', 'POST'])
def my_documents():
    if 'aadharnumber' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        img = request.files['file']
        if img:
                aadharnumber = str(session['aadharnumber'])
                query = {'aadharnumber':aadharnumber}
                law_data = lawyers_collection.find_one(query, {'_id':0})
                filename = session['aadharnumber']+ secure_filename(img.filename)
                img.save(filename)
                s3.upload_file(
                    Bucket = BUCKET_NAME,
                    Filename=filename,
                    Key = filename,
                    ExtraArgs={'ContentType': 'application/pdf'})
                
                query = {"aadharnumber": session['aadharnumber']}
                update = {"$push": {"docs": filename}}
                lawyers_collection.update_one(query, update)
                msg = "Upload Done !"
                os.remove(filename)
                return render_template('documents.html', data = law_data, message=msg) 
    query = {'aadharnumber':str(session['aadharnumber'])}
    law_data = lawyers_collection.find_one(query, {'_id':0})
    return render_template('documents.html', data = law_data)


# view documnet 

@app.route('/display_pdf/<filename>',methods=['GET'])
def display_pdf(filename):
    if 'aadharnumber' in session:

        response = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': filename,
                'ResponseContentDisposition': 'inline'
            },
        )
        return render_template('display_pdf.html', pdfUrl = response)
       
    return redirect(url_for('login'))

@app.route('/my_tasks', methods=['GET', 'POST','PUT'])
def my_tasks():
    if 'aadharnumber' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        taskname = request.form.get('taskname')
        taskdescription = request.form.get('taskdescription')
        eod = request.form.get('eod')
        
        # Handle the post using the session_aadharnumber 
        query = {"aadharnumber": session['aadharnumber']}
        update = {
            "$push": {
                "tasks": {
                    "taskname": taskname,
                    "taskdescription": taskdescription,
                    "eod": eod,
                    "status" : "todo"
                }
            }
        }
        lawyers_collection.update_one(query, update, upsert=True)

    # Retrieve tasks for the current user
    query = {"aadharnumber": session['aadharnumber']}
    user_tasks = lawyers_collection.find_one(query).get('tasks', [])
    return render_template('tasks.html', tasks = user_tasks)


@app.route('/my_tasks1', methods = ['GET', 'POST'])
def my_tasks1():
    if request.method == 'POST':
        task_index = int(request.form.get('task_index')) 
        new_status = request.form.get('new_status') 
        query = {"aadharnumber": session['aadharnumber']}
        update = {
            "$set": {
                f"tasks.{task_index}.status": new_status
            }
        }
        lawyers_collection.update_one(query, update)
        query = {"aadharnumber": session['aadharnumber']}
        user_tasks = lawyers_collection.find_one(query).get('tasks', [])
        return render_template('tasks.html', tasks = user_tasks, message = 'updated')
    query = {"aadharnumber": session['aadharnumber']}
    user_tasks = lawyers_collection.find_one(query).get('tasks', [])
    return render_template('tasks.html', tasks = user_tasks)


@app.route('/test')
def test():
    return render_template('translate.html')
#Handle Unknown routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return render_template('notFound.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host="0.0.0.0")