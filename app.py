from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    make_response,
    send_file,
    session,
    jsonify,
    json,
)
from pymysql import connections, cursors
import pymysql
import os
import boto3
from datetime import datetime 
from config import *

app = Flask(__name__)
app.config["SECRET_KEY"] = "amos-itp"

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost, port=3306, user=customuser, password=custompass, db=customdb
)
output = {}
table = "employee"


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("Index.html")

@app.route("/studRegister", methods=['GET', 'POST'])
def studRegister():
    return render_template('RegisterStudent.html')

@app.route("/about", methods=['POST'])
def about():
    return render_template("www.tarc.edu.my")


@app.route("/login", methods=["GET", "POST"])
def StudLogin():
    return render_template("StudLogin.html")

@app.route("/stud/submission")
def stud_submission():
    try:
        studid = session['userid']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM student s, progressReport p WHERE s.supervisorID = "
                       + "p.supervisorID AND studID = %s", ('2205123'))  
        classworks = cursor.fetchall()
        cursor.execute("SELECT * FROM submission WHERE studID = %s", ('2205123'))
        submissions = cursor.fetchall()
    
    except Exception as e:
        return str(e)
    
    finally:
        cursor.close()

    return render_template("StudSubmitReport.html", classworks=classworks, submissions=submissions)

@app.route("/stud/submit/<reportid>", methods=["GET", "POST"])
def submit(reportid):
    pdf = request.files["inputPdf"]
    studid = session['userid']
    studName = session['username']
    cursor = db_conn.cursor()
    handInDate = datetime.now()

    if pdf.filename == "":
        return "Please select a pdf to submit"

    try:
        cursor.execute("INSERT INTO submission (handInDate, reportID, studID) VALUES (%s, %s, %s)", (handInDate, reportid, '2205123'))
        db_conn.commit()
        cursor.execute("SELECT * FROM student WHERE studID = %s", ('2205123'))  
        students = cursor.fetchone()
        
        # Uplaod image file in S3 #
        report_file = "report_" + str(reportid) + "_" + str(students[1]) + "_" + str(students[0])
        s3 = boto3.resource("s3")

        print("Data inserted in MySQL RDS... uploading image to S3...")
        s3.Bucket(custombucket).put_object(Key=report_file, Body=pdf)
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

    print("all modification done...")
    return redirect(url_for('stud_submission'))

@app.route("/stud/unsubmit/<reportid>", methods=["GET", "POST"])
def unsubmit(reportid):
    pdf = request.files["inputPdf"]
    studid = session['userid']
    studName = session['username']
    cursor = db_conn.cursor()
    handInDate = datetime.now()

    if pdf.filename == "":
        return "Please select a pdf to submit"

    try:
        cursor.execute("INSERT INTO submission (handInDate, reportID, studID) VALUES (%s, %s, %s)", (handInDate, reportid, '2205123'))
        db_conn.commit()
        cursor.execute("SELECT * FROM student WHERE studID = %s", ('2205123'))  
        students = cursor.fetchone()
        
        # Uplaod image file in S3 #
        report_file = "report_" + str(reportid) + "_" + str(students[1]) + "_" + str(students[0]) + ".pdf"
        s3 = boto3.resource("s3")

        print("Data inserted in MySQL RDS... uploading image to S3...")
        s3.Bucket(custombucket).put_object(Key=report_file, Body=pdf)
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

    return redirect(url_for('stud_submission'))

# SUPERVISOR SITE
def list_files(filenames):
    """
    Function to list files in a given S3 bucket
    """
    s3 = boto3.client('s3')
    contents = []
    for image in s3.list_objects(Bucket=custombucket)['Contents']:
        for filename in filenames:
            s3_name = image['Key']
            if(filename == s3_name):
                contents.append(s3_name)

    return contents

def cleartext():
    response = " "
    return response

@app.route("/supervisor/view/stud", methods=['GET'])
def get_studs():
    try:
        supid = session['userid']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM student WHERE supervisorID = %s", (supid))
        students = cursor.fetchall()

    except Exception as e:
        return str(e)
    
    finally:
        cursor.close()

    return render_template('SupMyITP.html', students = students)

@app.route("/supervisor/view/report/<studid>", methods=['GET'])
def previewReport(studid):
    filenames = []
    try:
        supid = session['userid']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT reportID, reportName, dueDate FROM progressReport WHERE supervisorID=%s", (supid))
        classworks = cursor.fetchall()
        cursor.execute("SELECT * FROM student s, submission sb WHERE s.studID = sb.studID AND sb.studID = %s", (studid))
        reports = cursor.fetchall()
        
        for report in reports:
            filenames.append("report_" + str(report['reportID']) + "_" + str(report['studName']) + "_" + str(studid) + ".pdf")

        files = list_files(filenames)

    except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return render_template('SupViewReport.html', classworks = classworks, reports = reports, files=files)  

@app.route("/supervisor/login", methods=["GET", "POST"])
def sup_login():
    if request.method == 'GET':
        return render_template("SupLogin.html", msg="")
    else:
        cursor = db_conn.cursor()
        email = request.form["inputEmail"]
        password = request.form["inputPassword"]
        cursor.execute(
            "SELECT * FROM supervisor WHERE supervisorEmail=%s AND supervisorPassword=%s",
            (email, password)
        )
        record = cursor.fetchone()
        if record:
            session["loggedin"] = True
            session["userid"] = record[0]
            session["username"] = record[1]
            return redirect(url_for("get_studs"))
        else:
            msg = "Incorrect email/password.Try again!"
            return render_template("SupLogin.html", msg=msg)

@app.route('/update/report/<submissionid>', methods=['GET', 'POST'])
def update(submissionid):
    status = request.form['reportStatus']
    remark = request.form['remark']
    cursor = db_conn.cursor()

    try:
        cursor.execute("UPDATE submission SET status = %s, remark = %s WHERE submissionID=%s", (status, remark, submissionid))
        db_conn.commit()

    except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return "Save successfully"

@app.route('/preview/<filename>', methods=['GET'])
def preview(filename):
    if request.method == 'GET':
        s3 = boto3.resource('s3')
        file = s3.Object(custombucket, filename).get()
        response = make_response(file['Body'].read())
        response.headers['Content-Type'] = 'application/pdf'
        return response
    
@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    if request.method == 'GET':
        s3 = boto3.resource('s3')
        output = f"/media/{filename}"
        s3.Bucket(bucket).download_file(Key=filename, Filename=output)
        return send_file(output, as_attachment=True)


@app.route("/company/register", methods=["GET", "POST"])
def comp_register():
    return render_template("CompRegister.html")


@app.route("/company/Register", methods=["GET", "POST"])
def Comp_Register():
    compName = request.form["inputName"]
    compEmail = request.form["inputEmail"]
    compPassword = request.form["inputPassword"]
    compPhoneNo = request.form["inputPhoneNumber"]
    compAddress = request.form["inputAddress"]
    compWebsite = request.form["inputWebsite"]
    socialMedia = request.form["inputSocialMedia"]
    registerStatus = "pending"
    committeeID = None
    compLogo = request.files["inputLogo"]
    businessLicense = request.files["inputLicense"]

    insert_sql = "INSERT INTO company (compName, compEmail, compPassword, compPhoneNo, compAddress, compWebsite, socialMedia, registerStatus, committeeID)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if compLogo.filename == "":
        return "Please select an image for logo"

    if businessLicense.filename == "":
        return "Please select an image for license"

    try:
        cursor.execute(
            insert_sql,
            (
                compName,
                compEmail,
                compPassword,
                compPhoneNo,
                compAddress,
                compWebsite,
                socialMedia,
                registerStatus,
                committeeID,
            ),
        )
        db_conn.commit()
        compID = cursor.lastrowid
        # Uplaod image file in S3 #
        logo_file = "comp-id-" + str(compID) + "_logo"
        license_file = "comp-id-" + str(compID) + "_license"
        s3 = boto3.resource("s3")

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=logo_file, Body=compLogo)
            s3.Bucket(custombucket).put_object(Key=license_file, Body=businessLicense)
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

    return redirect(url_for("home"))


@app.route("/company/login", methods=["GET", "POST"])
def comp_login():
    return render_template("CompLogin.html", msg="")


@app.route("/company/Login", methods=["GET", "POST"])
def Comp_Login():
    msg = ""
    cursor = db_conn.cursor()
    if request.method == "POST":
        email = request.form["inputEmail"]
        password = request.form["inputPassword"]
        cursor.execute(
            "SELECT * FROM company WHERE compEmail=%s AND compPassword=%s",
            (email, password),
        )
        record = cursor.fetchone()
        if record:
            session["loggedin"] = True
            session["userid"] = record[0]
            session["username"] = record[1]
            return redirect(url_for("comp_offers"))
        else:
            msg = "Incorrect email/password.Try again!"
    return render_template("CompLogin.html", msg=msg)


@app.route("/company/offers", methods=["GET", "POST"])
def comp_offers():
    return render_template("CompOffers.html")


@app.route("/company/GetOffers", methods=["POST"])
def comp_get_offers():
    try:
        db_conn = connections.Connection(
            host=customhost,
            port=3306,
            user=customuser,
            password=custompass,
            db=customdb,
            cursorclass=cursors.DictCursor,
        )
        cursor = db_conn.cursor()
        if request.method == "POST":
            draw = request.form["draw"]
            row = int(request.form["start"])
            rowperpage = int(request.form["length"])
            searchValue = request.form["search[value]"]
            compID = session["userid"]

            ## Total number of records without filtering
            cursor.execute("SELECT count(*) as allcount from offer WHERE compID=%s", compID)
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount["allcount"]

            ## Total number of records with filtering
            likeString = "%" + searchValue + "%"
            cursor.execute(
                "SELECT count(*) as allcount from offer WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s) AND compID=%s",
                (likeString, likeString, likeString, likeString, likeString, compID),
            )
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute(
                    "SELECT * FROM offer WHERE compID=%s ORDER BY offerStatus asc, datePosted desc limit %s, %s;",
                    (compID, row, rowperpage),
                )
                offerlist = cursor.fetchall()
            else:
                cursor.execute(
                    "SELECT * FROM offer WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s) AND compID=%s ORDER BY offerStatus asc, datePosted desc",
                    (likeString, likeString, likeString, likeString, likeString, compID),
                )
                offerlist = cursor.fetchall()
            
            data = []
            for row in offerlist:
                print(row["offerID"])
                data.append(
                    {
                        "offerID": row["offerID"],
                        "datePosted": row["datePosted"].strftime("%d-%m-%Y %I:%M:%S %p"),
                        "position": row["position"],
                        "allowance": row["allowance"],
                        "offerStatus": row["offerStatus"],
                    }
                )
                
            response = {
                "draw": draw,
                "iTotalRecords": totalRecords,
                "iTotalDisplayRecords": totalRecordwithFilter,
                "aaData": data,
            }
            return jsonify(response)
    except Exception as e:
        print(e)
    finally:
        cursor.close()


@app.route("/company/addoffer", methods=["GET", "POST"])
def comp_add_offer():
    return render_template("CompAddOffer.html")


@app.route("/company/AddOffer", methods=["GET", "POST"])
def Comp_Add_Offer():
    position = request.form["inputPosition"]
    allowance = request.form["inputAllowance"]
    duration = request.form["inputDuration"]
    prerequisite = request.form["inputPrerequisite"]
    language = request.form["inputLanguage"]
    location = request.form["inputLocation"]
    description = request.form["inputDescription"]
    datePosted = datetime.now()
    offerStatus = "active"
    compID = session["userid"]

    insert_sql = "INSERT INTO offer (position, allowance, duration, prerequisite, language, location, description, datePosted, offerStatus, compID)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(
            insert_sql,
            (
                position,
                allowance,
                duration,
                prerequisite,
                language,
                location,
                description,
                datePosted,
                offerStatus,
                compID,
            ),
        )
        db_conn.commit()

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

    return redirect(url_for("comp_offers"))


# EXAMPLE UPDATE RDS AND S3
@app.route("/addemp", methods=["GET", "POST"])
def AddEmp():
    emp_id = request.form["emp_id"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    pri_skill = request.form["pri_skill"]
    location = request.form["location"]
    emp_image_file = request.files["emp_image_file"]

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
        s3 = boto3.resource("s3")

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(
                Key=emp_image_file_name_in_s3, Body=emp_image_file
            )
            bucket_location = boto3.client("s3").get_bucket_location(
                Bucket=custombucket
            )
            s3_location = bucket_location["LocationConstraint"]

            if s3_location is None:
                s3_location = ""
            else:
                s3_location = "-" + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location, custombucket, emp_image_file_name_in_s3
            )

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template("AddEmpOutput.html", name=emp_name)

@app.route("/student/studRegister", methods=['GET','POST'])
def stud_Register():
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
    insert_sql = "INSERT INTO student (studID, studName, studIC, studPhone, studGender, studUniEmail, studPersonalEmail, studAddress, studLevel, studProgramme, studTutGrp, CGPA, supervisorID)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(get_supervisorid_sql, superVisorName)
        superVisorID = cursor.fetchone()
        cursor.execute(insert_sql, (studID, studName, studIC, studPhone, studGender, studUniEmail, studPersonalEmail, studAddress, studLevel, studProgramme, studTutGrp, CGPA, superVisorID))
        db_conn.commit()

    finally:
        cursor.close()

    return redirect("/")

@app.route("/viewOffers", methods=['GET','POST'])
def viewoffers():
    try:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT offerID, position, allowance, duration, prerequisite, language, location, datePosted, offerStatus, compName FROM offer O, company C WHERE O.compID = C.compID")
        offers = cursor.fetchall()
        
        # contents = list_files

    except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return render_template('ViewOffers.html', offers = offers) 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
