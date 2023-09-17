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
    send_file,
)
from pymysql import connections, cursors
import pymysql
import os
import boto3
from datetime import datetime
from config import *
from io import BytesIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "amos-itp"

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost, port=3306, user=customuser, password=custompass, db=customdb, connect_timeout=86400
)


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("Index.html")


@app.route("/about", methods=["POST"])
def about():
    return render_template("www.tarc.edu.my")


@app.route("/login", methods=["GET", "POST"])
def StudLogin():
    return render_template("StudLogin.html")

@app.route("/stud/submission")
def stud_submission():
    supid = session['userid']
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT supervisorID FROM student WHERE studentID=%s", (supid))  
    cursor.execute("SELECT reportID, reportName, dueDate FROM progressReport WHERE supervisorID=%s", (supid))
    classworks = cursor.fetchall()
    return render_template("StudSubmitReport.html", classworks=classworks)


# SUPERVISOR SITE
def list_files():
    """
    Function to list files in a given S3 bucket
    """
    s3 = boto3.client('s3')
    contents = []
    for image in s3.list_objects(Bucket=custombucket)['Contents']:
        file = image['Key']
        if(file.endswith('.pdf')):
            contents.append(file)
        # contents.append(f'https://{custombucket}.s3.amazonaws.com/{image}')

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
    try:
        supid = session['userid']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT reportID, reportName, dueDate FROM progressReport WHERE supervisorID=%s", (supid))
        classworks = cursor.fetchall()
        cursor.execute("SELECT * FROM submission WHERE studID = %s", (studid))
        reports = cursor.fetchall()
        
        # contents = list_files

    except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return render_template('SupViewReport.html', classworks = classworks, reports = reports, files="test")  

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


@app.route("/admin/compdetails/<compid>", methods=["GET", "POST"])
def CompDetails(compid):
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM company WHERE compID=%s", (compid))
    compDetails = cursor.fetchall()
    cursor.close()

    s3 = boto3.client("s3")
    contents = []
    for image in s3.list_objects(Bucket=custombucket)["Contents"]:
        file = image["Key"]
        if file.startswith("comp-id-" + compid):
            contents.append(file)
    return render_template("CompDetails.html", comp=compDetails, file=contents)
    # return render_template('CompDetails.html', comp = compDetails)


@app.route("/admin/registredcomp", methods=["GET"])
def RegisteredComp():
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT compID,CompName,registerStatus FROM company WHERE registerStatus='active'"
    )
    company = cursor.fetchall()
    cursor.close()
    return render_template("RegisteredComp.html", comp=company)


@app.route("/admin/compregistration", methods=["GET"])
def CompRequest():
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT compID,CompName,registerStatus FROM company WHERE registerStatus='pending'"
    )
    company = cursor.fetchall()
    cursor.close()
    return render_template("CompRegistration.html", comp=company)


@app.route("/company/Register", methods=["GET", "POST"])
def Comp_Register():
    compName = request.form["inputName"]
    compEmail = request.form["inputEmail"]
    compPassword = request.form["inputPassword"]
    compPhoneNo = request.form["inputPhoneNumber"]
    compAddress = request.form["inputAddress"]
    compWebsite = request.form["inputWebsite"]
    socialMedia = request.form["inputSocialMedia"]
    registerStatus = "Pending"
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


@app.route("/previewImg/<file>", methods=["GET"])
def previewImg(file):
    if request.method == "GET":
        s3 = boto3.resource("s3")
        file1 = s3.Object(custombucket, file).get()
    img = file1["Body"].read()
    return send_file(BytesIO(img), mimetype="image/jpeg")
    # return file['Body'].read()


@app.route("/company/offers", methods=["GET", "POST"])
def comp_offers():
    return render_template("CompOffers.html")


@app.route("/company/GetOffers", methods=["POST"])
def Comp_Get_Offers():
    try:
        db_conn2 = connections.Connection(
            host=customhost,
            port=3306,
            user=customuser,
            password=custompass,
            db=customdb,
            cursorclass=cursors.DictCursor,
        )
        cursor = db_conn2.cursor()
        if request.method == "POST":
            draw = request.form["draw"]
            row = int(request.form["start"])
            rowperpage = int(request.form["length"])
            searchValue = request.form["search[value]"]
            compID = session["userid"]

            ## Total number of records without filtering
            cursor.execute(
                "SELECT count(*) as allcount from offer WHERE compID=%s", compID
            )
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
                    "SELECT * FROM offer WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s) AND compID=%s ORDER BY offerStatus asc, datePosted desc limit %s, %s;",
                    (
                        likeString,
                        likeString,
                        likeString,
                        likeString,
                        likeString,
                        compID,
                        row,
                        rowperpage,
                    ),
                )
                offerlist = cursor.fetchall()

            data = []
            for row in offerlist:
                data.append(
                    {
                        "offerID": row["offerID"],
                        "datePosted": row["datePosted"].strftime(
                            "%d-%m-%Y %I:%M:%S %p"
                        ),
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
        db_conn2.close()


@app.route("/company/offerdetails", methods=["GET", "POST"])
def comp_offer_details():
    offerID = request.args.get("id")
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT * FROM offer WHERE offerID=%s",
        (offerID),
    )
    record = cursor.fetchone()
    return render_template(
        "CompOfferDetails.html",
        offerID=record[0],
        position=record[1],
        allowance=record[2],
        duration=record[3],
        prerequisite=record[4],
        language=record[5],
        location=record[6],
        description=record[7],
        datePosted=record[8].strftime("%d-%m-%Y %I:%M:%S %p"),
        offerStatus=record[9],
    )


@app.route("/company/GetOfferApplications", methods=["POST"])
def Comp_Get_Offer_Applications():
    try:
        db_conn2 = connections.Connection(
            host=customhost,
            port=3306,
            user=customuser,
            password=custompass,
            db=customdb,
            cursorclass=cursors.DictCursor,
        )
        cursor = db_conn2.cursor()
        if request.method == "POST":
            draw = request.form["draw"]
            row = int(request.form["start"])
            rowperpage = int(request.form["length"])
            searchValue = request.form["search[value]"]
            offerID = request.args.get("id")
            ## Total number of records without filtering
            cincai = request.form
            cursor.execute(
                "SELECT count(*) as allcount from application WHERE offerID=%s", offerID
            )
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount["allcount"]

            ## Total number of records with filtering
            likeString = "%" + searchValue + "%"
            cursor.execute(
                "SELECT COUNT(*) AS allcount FROM application WHERE appStatus LIKE %s AND offerID=%s ORDER BY CASE appStatus WHEN 'pending' THEN 0 WHEN 'accepted' THEN 1 WHEN 'rejected' THEN 2 END ASC, appliedDateTime ASC;",
                (likeString, offerID),
            )
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute(
                    "SELECT * FROM application a, student s WHERE a.studID=s.studID AND offerID=%s ORDER BY CASE appStatus WHEN 'pending' THEN 0 WHEN 'accepted' THEN 1 WHEN 'rejected' THEN 2 END ASC, appliedDateTime ASC LIMIT %s, %s;",
                    (offerID, row, rowperpage),
                )
                offerlist = cursor.fetchall()
            else:
                cursor.execute(
                    "SELECT * FROM application a, student s WHERE a.studID=s.studID AND appStatus LIKE %s AND offerID=%s ORDER BY CASE appStatus WHEN 'pending' THEN 0 WHEN 'accepted' THEN 1 WHEN 'rejected' THEN 2 END ASC, appliedDateTime ASC LIMIT %s, %s;",
                    (likeString, offerID, row, rowperpage),
                )
                offerlist = cursor.fetchall()

            data = []
            for row in offerlist:
                data.append(
                    {
                        "appID": row["appID"],
                        "appliedDateTime": row["appliedDateTime"].strftime(
                            "%d-%m-%Y %I:%M:%S %p"
                        ),
                        "studID": row["studID"],
                        "studName": row["studName"],
                        "studLevel": row["studLevel"],
                        "studProgramme": row["studProgramme"],
                        "CGPA": format(row["CGPA"], ".4f"),
                        "appStatus": row["appStatus"],
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
        db_conn2.close()
        

@app.route("/company/appdetails", methods=["GET", "POST"])
def comp_app_details():
    appID = request.args.get("id")
    try:
        db_conn2 = connections.Connection(
            host=customhost,
            port=3306,
            user=customuser,
            password=custompass,
            db=customdb,
            cursorclass=cursors.DictCursor,
        )
        cursor = db_conn2.cursor()
        cursor.execute(
            "SELECT * FROM offer o, application a, student s WHERE o.offerID=a.offerID AND a.studID=s.studID AND a.appID=%s;",
            (appID),
        )

        record = cursor.fetchone()
        s3 = boto3.client("s3")
        contents = []
        for image in s3.list_objects(Bucket=custombucket)["Contents"]:
            file = image["Key"]
            if file.startswith("stud-id-" + record['studID'] + '_resume'):
                contents.append(file)
        return render_template("CompAppDetails.html", appdetails=record, file=contents)
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        db_conn2.close()


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
    offerStatus = "Active"
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
