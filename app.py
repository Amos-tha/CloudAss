from flask import Flask, render_template, request, redirect
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)
output = {}
table = 'company'

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('Index.html')

@app.route("/about", methods=['POST'])
def about():
    return render_template('www.tarc.edu.my')

@app.route("/login", methods=['GET', 'POST'])
def StudLogin():
    return render_template('StudLogin.html')

@app.route("/company/register", methods=['GET','POST'])
def comp_register():
    return render_template('RegisterComp.html')

@app.route("/admin/compdetails/<compid>", methods=["GET",'POST'])
def CompDetails(compid):
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM company WHERE compID=%s" , (compid))
    compDetails = cursor.fetchall()
    cursor.close()

    s3 = boto3.client('s3')
    contents = []
    for image in s3.list_objects(Bucket=custombucket)['Contents']:
        file = image['Key']
        if(file.startswith('comp-id-'+compid)):
            contents.append(file)    
    return render_template('CompDetails.html', comp = compDetails, file = contents)
        #return render_template('CompDetails.html', comp = compDetails)

@app.route("/admin/registredcomp", methods=['GET'])
def RegisteredComp():
    cursor = db_conn.cursor()
    cursor.execute("SELECT compID,CompName,registerStatus FROM company WHERE registerStatus='active'")
    company = cursor.fetchall()
    cursor.close()
    return render_template("RegisteredComp.html", comp = company)

@app.route("/admin/compregistration", methods=['GET'])
def CompRequest():
    cursor = db_conn.cursor()
    cursor.execute("SELECT compID,CompName,registerStatus FROM company WHERE registerStatus='pending'")
    company = cursor.fetchall()
    cursor.close()
    return render_template("CompRegistration.html", comp = company)

@app.route("/company/Register", methods=['GET','POST'])
def Comp_Register():
    compName = request.form['inputName']
    compEmail = request.form['inputEmail']
    compPassword = request.form['inputPassword']
    compPhoneNo = request.form['inputPhoneNumber']
    compAddress = request.form['inputAddress']
    compWebsite = request.form['inputWebsite']
    socialMedia = request.form['inputSocialMedia']
    registerStatus = "pending"
    committeeID = None
    compLogo = request.files['inputLogo']
    businessLicense = request.files['inputLicense']

    insert_sql = "INSERT INTO company (compName, compEmail, compPassword, compPhoneNo, compAddress, compWebsite, socialMedia, registerStatus, committeeID)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if compLogo.filename == "":
        return "Please select an image for logo"
    
    if businessLicense.filename == "":
        return "Please select an image for license"

    try:
        cursor.execute(insert_sql, (compName, compEmail, compPassword, compPhoneNo, compAddress, compWebsite, socialMedia, registerStatus, committeeID))
        db_conn.commit()
        compID = cursor.lastrowid
        # Uplaod image file in S3 #
        logo_file = "comp-id-" + str(compID) + "_logo"
        license_file = "comp-id-" + str(compID) + "_license"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=logo_file, Body=compLogo)
            s3.Bucket(custombucket).put_object(Key=license_file, Body=businessLicense)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return redirect("/")

@app.route('/previewImg/<file>', methods=['GET'])
def preview(file):
    if request.method == 'GET':
        s3 = boto3.resource('s3')
        file = s3.Object(custombucket, file).get()
        return file

@app.route("/company/login", methods=['GET','POST'])
def comp_login():
    return render_template('CompLogin.html')

@app.route("/company/offers", methods=['GET','POST'])
def comp_offers():
    return render_template('CompOffers.html')

#EXAMPLE UPDATE RDS AND S3
@app.route("/addemp", methods=['GET','POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
