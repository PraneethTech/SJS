from flask import Flask # type: ignore
import os
from flask import Blueprint, jsonify, make_response, redirect, render_template, request, session, url_for, flash # type: ignore
import openai
import confidential as keys
import boto3
from pymongo import MongoClient
import bcrypt # type: ignore
from werkzeug.utils import secure_filename # type: ignore

app = Flask(__name__)

aws_access_key_id = 'YOUR_AWS_ACCESS_KEY_ID'
aws_secret_access_key = 'YOUR_AWS_SECRET_ACCESS_KEY'
aws_region = 'YOUR_AWS_REGION'

s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
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

@app.route('/my_documents', methods=['GET', 'POST'])
def my_documents():
    if 'aadharnumber' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        img = request.files['file']
        if img:
            aadharnumber = str(session['aadharnumber'])
            query = {'aadharnumber': aadharnumber}
            law_data = lawyers_collection.find_one(query, {'_id': 0})
            filename = session['aadharnumber'] + secure_filename(img.filename)
            img.save(filename)
            try:
                s3.upload_file(
                    Bucket=BUCKET_NAME,
                    Filename=filename,
                    Key=filename,
                    ExtraArgs={'ContentType': 'application/pdf'}
                )
                query = {"aadharnumber": session['aadharnumber']}
                update = {"$push": {"docs": filename}}
                lawyers_collection.update_one(query, update)
                msg = "Upload Done !"
                os.remove(filename)
                return render_template('documents.html', data=law_data, message=msg)
            except Exception as e:
                os.remove(filename)
                return render_template('error.html', error=str(e))

    query = {'aadharnumber': str(session['aadharnumber'])}
    law_data = lawyers_collection.find_one(query, {'_id': 0})
    return render_template('documents.html', data=law_data)


@app.route('/display_pdf/<filename>', methods=['GET'])
def display_pdf(filename):
    if 'aadharnumber' in session:
        try:
            response = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': filename,
                    'ResponseContentDisposition': 'inline'
                },
            )
            return render_template('display_pdf.html', pdfUrl=response)
        except Exception as e:
            return render_template('error.html', error=str(e))
    return redirect(url_for('login'))