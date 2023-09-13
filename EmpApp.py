from flask import Flask, render_template, request, make_response
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
    return render_template('index.html')
    # return render_template('AddEmp.html')


@app.route("/about")
def about():
    return render_template('ProgressReport.html')


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

# @app.route("/myITP", method=['POST'])
# def getStudents():
#     cursor = db_conn.cursor()
#     cursor.execute("SELECT * FROM Student")
#     students = cursor.fetchall()
#     cursor.close()

#     return render_template("ViewReport.html", maxStud = len(), students = students)


@app.route("/view")
def previewReport(id=None):
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(custombucket)
    bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
    s3_location = (bucket_location['LocationConstraint'])
    summaries = my_bucket.objects.all()
    contents = []
    for image in summaries:
        contents.append(image.key)

    return render_template('ViewReport.html', my_bucket=bucket, list_of_files=contents)

    test = s3.Object(custombucket, "test.pdf").get()
    response = make_response(test['Body'].read())
    response.headers['Content-Type'] = 'application/pdf'
    # response.headers['Content-Disposition'] = \
    #     'inline; filename=test.pdf' % 'test.pd'
    return render_template('ViewReport.html', test=test)  
    
    # list_file = []
    # stud_id = request.form['stud_id']
    # filename = stud_id + " "

    # s3 = boto3.resource('s3')
    # for item in s3.Bucket(custombucket).get_object(Bucket=custombucket, Key=filename)['Contents']:
    #     list_file.append(item)
    # return list_file

# @app.route('/download/<filename>', methods=['GET'])
# def download(upload_id):
#     upload = Upload.query.filter_by(id=upload_id).first()
#     return send_file(BytesIO(upload.data),
#                      download_name=upload.filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

