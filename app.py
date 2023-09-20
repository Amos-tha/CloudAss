import datetime
from io import BytesIO
from flask import Flask, render_template, request, redirect, send_file, session, url_for
from pymysql import NULL, connections
import os
import boto3
import pymysql
from config import *

app = Flask(__name__)
app.config["SECRET_KEY"] = "amos-itp"

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

@app.route("/about", methods=['POST'])
def about():
    return render_template('www.tarc.edu.my')

@app.route("/company/register", methods=['GET','POST'])
def comp_register():
    return render_template('RegisterComp.html')

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

@app.route("/student/studRegisterPage", methods=['GET','POST'])
def stud_register_page():
    return render_template('RegisterStudent.html')

@app.route("/student/studRegister", methods=['GET','POST'])
def stud_register():
    if request.method == "POST":
        studID = request.form['inputstudID']
        studUniEmail = request.form['inputUniEmail']
        studLevel = request.form['inputLevel']
        studProgramme = request.form['inputProgramme']
        studTutGrp = request.form['inputTutGrp']
        CGPA = request.form['inputCGPA']
        superVisorName = request.form['inputSupervisor']

        studName = request.form['inputName']
        studIC = request.form['inputIC']
        studGender = request.form['inputGender']
        studPersonalEmail = request.form['inputPersonalEmail']
        studPhone = request.form['inputPhone']
        studAddress = request.form['inputAddress']

        studResume = request.files["inputResume"]

        get_supervisorid_sql = "SELECT superVisorID FROM supervisor WHERE superVisorName = (%s)"
        insert_sql = "INSERT INTO student (studID, studName, studIC, studPhone, studGender, studUniEmail, studPersonalEmail, studAddress, studLevel, studProgramme, studTutGrp, CGPA, supervisorID)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor = db_conn.cursor()

        if studResume.filename == "":
            return "Please upload your resume!"

        try:
            cursor.execute(get_supervisorid_sql, superVisorName)
            superVisorID = cursor.fetchone()
            cursor.execute(insert_sql, (studID, studName, studIC, studPhone, studGender, studUniEmail, studPersonalEmail, studAddress, studLevel, studProgramme, studTutGrp, CGPA, superVisorID))
            db_conn.commit()

            resume_file = "stud-id-" + str(studID) + "_resume.pdf"
            s3 = boto3.resource("s3")

            try:
                print("Data inserted in MySQL RDS... uploading resume to S3...")
                s3.Bucket(custombucket).put_object(Key=resume_file, Body=studResume)
                bucket_location = boto3.client("s3").get_bucket_location(
                    Bucket=custombucket
                )
                s3_location = bucket_location["LocationConstraint"]

                if s3_location is None:
                    s3_location = ""
                else:
                    s3_location = "-" + s3_location

            except Exception as e:
                return str(e)

        finally:
            cursor.close()

    return render_template("StudLogin.html", msg="")

@app.route("/viewOffers", methods=['GET','POST'])
def viewoffers():
    msg = request.args.get("msg")
    if msg is None:
        msg = ''
    
    try:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT offerID, position, allowance, duration, prerequisite, language, location, datePosted, offerStatus, O.compID, compName FROM offer O, company C WHERE O.compID = C.compID AND offerStatus LIKE 'Active%'")
        offers = cursor.fetchall()

    except Exception as e:
            print(e)
            return str(e)

    finally:
        cursor.close()

    s3 = boto3.client("s3")
    contents = []
    for offer in offers:
        compID = offer['compID']
        for image in s3.list_objects(Bucket=custombucket)["Contents"]:
            file = image["Key"]
            if file.startswith("comp-id-" + str(compID) + "_logo"):
                contents.append(file)

    return render_template('ViewOffers.html', offers=offers, contents=contents, msg=msg) 

@app.route("/student/login", methods=["GET", "POST"])
def stud_login():
    msg = ""
    cursor = db_conn.cursor()
    if request.method == "POST":
        email = request.form["inputUniEmail"]
        ic = request.form["inputIC"]
        cursor.execute(
            "SELECT * FROM student WHERE studUniEmail=%s AND studIC=%s",
            (email, ic),
        )
        record = cursor.fetchone()
        if record:
            session["loggedin"] = True
            session["userid"] = record[0]
            session["username"] = record[1]
            return redirect(url_for("viewoffers"))
        else:
            msg = "Incorrect university email/NRIC. Try again!"
    return render_template("StudLogin.html", msg=msg)

@app.route('/previewImg/<file>', methods=['GET'])
def preview(file):
    if request.method == 'GET':
        s3 = boto3.resource('s3')
        file1 = s3.Object(custombucket, file).get()
    img = file1['Body'].read()
    return send_file(BytesIO(img), mimetype='image/jpeg')
    # return file['Body'].read()

@app.route("/student/offerDetails", methods=['GET','POST'])
def view_offer_details():
    if request.method == "GET":
        selectedOfferID = request.args.get("selectedOffer")

    try:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT offerID, position, allowance, duration, prerequisite, language, location, datePosted, offerStatus, O.compID, compName FROM offer O, company C WHERE O.compID = C.compID AND offerID = %s", (selectedOfferID))
        offerdetails = cursor.fetchone()

    except Exception as e:
            print(e)    
            return str(e)

    finally:
        cursor.close()

    s3 = boto3.client("s3")
    contents = []
    compID = offerdetails['compID']
    for image in s3.list_objects(Bucket=custombucket)["Contents"]:
        file = image["Key"]
        if file.startswith("comp-id-" + str(compID) + "_logo"):
            contents.append(file)

    return render_template('OfferDetails.html', offerdetails = offerdetails, contents=contents)

@app.route("/student/applyOffer", methods=['GET','POST'])
def apply_offer():
    if request.method == "POST":
        selectedOfferID = request.form['selectedOffer']
        studID = session["userid"]
        datetimeNow = datetime.datetime.now()
        insert_sql = "INSERT INTO application (appStatus, appliedDateTime, studID, offerID) VALUES (%s, %s, %s, %s)"
        cursor = db_conn.cursor()

        try:
            cursor.execute(insert_sql, ("Pending", datetimeNow, str(studID), selectedOfferID))
            db_conn.commit()
            appID = cursor.lastrowid
            msg = "You have successfully apply for the offer."

        except Exception as e: 
                return str(e)

        finally:
            cursor.close()

    return redirect(url_for("viewoffers", msg=msg))

@app.route("/student/viewDetails", methods=['GET','POST'])
def stud_view_details():

    msg = request.args.get("msg")
    if msg is None:
        msg = ''

    if request.method == "GET":
        studID = session["userid"]

    try:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT studID, studName, studIC, studPhone, studGender, studUniEmail, studPersonalEmail, studAddress, studLevel, studProgramme, studTutGrp, CGPA, S.supervisorID, V.supervisorName FROM student S, supervisor V WHERE S.supervisorID = V.supervisorID AND studID = %s", (studID))
        studDetails = cursor.fetchone()

    except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return render_template('StudentDetails.html', studDetails=studDetails, msg=msg)

@app.route("/student/studUpdate", methods=['GET','POST'])
def stud_update():
    if request.method == "POST":
        studID = request.form['inputstudID']
        studUniEmail = request.form['inputUniEmail']
        studLevel = request.form['inputLevel']
        studProgramme = request.form['inputProgramme']
        studTutGrp = request.form['inputTutGrp']
        CGPA = request.form['inputCGPA']
        superVisorName = request.form['inputSupervisor']

        studName = request.form['inputName']
        studIC = request.form['inputIC']
        studGender = request.form['inputGender']
        studPersonalEmail = request.form['inputPersonalEmail']
        studPhone = request.form['inputPhone']
        studAddress = request.form['inputAddress']

        get_supervisorid_sql = "SELECT superVisorID FROM supervisor WHERE superVisorName = (%s)"
        update_sql = "UPDATE student SET studName = %s, studIC = %s, studPhone = %s, studGender = %s, studUniEmail = %s, studPersonalEmail = %s, studAddress = %s, studLevel = %s, studProgramme = %s, studTutGrp = %s, CGPA = %s, supervisorID = %s WHERE studID = %s" 
        cursor = db_conn.cursor()

        try:
            cursor.execute(get_supervisorid_sql, superVisorName)
            superVisorID = cursor.fetchone()
            cursor.execute(update_sql, (studName, studIC, studPhone, studGender, studUniEmail, studPersonalEmail, studAddress, studLevel, studProgramme, studTutGrp, CGPA, superVisorID, studID))
            db_conn.commit()
            msg = "Information updated."

        except Exception as e: 
            return str(e)

        finally:
            cursor.close()

    return redirect(url_for("stud_view_details", msg=msg))

@app.route("/student/viewDoc", methods=['GET','POST'])
def stud_viewDoc_page():

    msg = request.args.get("msg")
    if msg is None:
        msg = ''

    return render_template('StudUploadDoc.html')

@app.route("/student/uploadDoc", methods=['GET','POST'])
def stud_uploadDoc():
    if request.method == "POST":

        studID = session["userid"]

        companyAcceptanceLetter = request.files["inputCompanyAcceptanceLetter"]
        letterOfIdemnity = request.files["inputLetterOfIdemnity"]
        acknowledgeForm = request.files["inputAcknowledgeForm"]

        # if studResume.filename == "":
        #     return "Please upload your resume!"
        
        # if companyAcceptanceLetter.filename == "":
        #     return "Please upload your acceptance letter!"
        
        # if letterOfIdemnity.filename == "":
        #     return "Please upload your resume!"
        
        # if acknowledgeForm.filename == "":
        #     return "Please upload your resume!"


        companyAcceptanceLetter_file = "stud-id-" + str(studID) + "_CAL.pdf"
        letterOfIdemnity_file = "stud-id-" + str(studID) + "_LOI.pdf"
        acknowledgeForm_file = "stud-id-" + str(studID) + "_AF.pdf"
        s3 = boto3.resource("s3")

        try:
            # check if document exist
            try:
                s3.Bucket(custombucket).Object(companyAcceptanceLetter_file).load
            except:
                if e.response['Error']['Code'] == "404":
                    s3.Bucket(custombucket).put_object(Key=companyAcceptanceLetter_file, Body=companyAcceptanceLetter)
                else:
                    return str(e)
            else:
               s3.Object(custombucket, companyAcceptanceLetter_file).delete()
               s3.Bucket(custombucket).put_object(Key=companyAcceptanceLetter_file, Body=companyAcceptanceLetter)

            try:
                s3.Bucket(custombucket).Object(letterOfIdemnity_file).load
            except:
                if e.response['Error']['Code'] == "404":
                    s3.Bucket(custombucket).put_object(Key=letterOfIdemnity_file, Body=letterOfIdemnity)
                else:
                    return str(e)
            else:
               s3.Object(custombucket, letterOfIdemnity_file).delete()
               s3.Bucket(custombucket).put_object(Key=letterOfIdemnity_file, Body=letterOfIdemnity)
            
            try:
                s3.Bucket(custombucket).Object(letterOfIdemnity_file).load
            except:
                if e.response['Error']['Code'] == "404":
                    s3.Bucket(custombucket).put_object(Key=acknowledgeForm_file, Body=acknowledgeForm)
                else:
                    return str(e)
            else:
               s3.Object(custombucket, acknowledgeForm_file).delete()
               s3.Bucket(custombucket).put_object(Key=acknowledgeForm_file, Body=acknowledgeForm)

            bucket_location = boto3.client("s3").get_bucket_location(
                Bucket=custombucket
            )
            s3_location = bucket_location["LocationConstraint"]

            if s3_location is None:
                s3_location = ""
            else:
                s3_location = "-" + s3_location
            
            msg = "Documents uploaded."

        except Exception as e:
            return str(e)

    stud_viewDoc_page
    return redirect(url_for("stud_viewDoc_page", msg=msg))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
