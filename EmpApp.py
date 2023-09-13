from flask import Flask, render_template, request, make_response, send_file
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
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('Index.html')
    # return render_template('AddEmp.html')


@app.route("/about")
def about():
    return render_template('ViewMyStudent.html')


@app.route("/addemp", methods=['POST'])
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

def list_files():
    """
    Function to list files in a given S3 bucket
    """
    s3 = boto3.client('s3')
    contents = []
    for image in s3.list_objects(Bucket=custombucket)['Contents']:
        contents.append(image)
        # contents.append(f'https://{custombucket}.s3.amazonaws.com/{image}')

    return contents

@app.route("/viewmystud")
def test():
    return render_template('ViewMyStudent.html')

# @app.route("/myITP", method=['POST'])
# def getStudents():
#     cursor = db_conn.cursor()
#     cursor.execute("SELECT * FROM Student")
#     students = cursor.fetchall()
#     cursor.close()

#     return render_template("ViewReport.html", maxStud = len(), students = students)

@app.route("/view")
def previewReport(id=None):
#     return render_template('ViewReport.html', my_bucket=bucket, list_of_files=contents)

#     test = s3.Object(custombucket, "test.pdf").get()
#     response = make_response(test['Body'].read())
#     response.headers['Content-Type'] = 'application/pdf'
#     # response.headers['Content-Disposition'] = \
#     #     'inline; filename=test.pdf' % 'test.pd'
    contents = list_files()
    return render_template('ViewReport.html', contents=contents)  
    
#     # list_file = []
#     # stud_id = request.form['stud_id']
#     # filename = stud_id + " "

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    if request.method == 'GET':
        s3 = boto3.resource('s3')
        output = f"downloads/{filename}"
        s3.Bucket(bucket).download_file(filename, output)
        return send_file(output, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

