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
    flash,
)
import pymysql
from pymysql import NULL, connections, cursors
import os
import boto3
from datetime import datetime
import datetime
from io import BytesIO
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
    db=customdb,
    connect_timeout=86400,
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


@app.route("/supervisor/view/stud", methods=["GET"])
def get_studs():
    try:
        supid = session["userid"]
        cursor = db_conn.cursor(cursors.DictCursor)
        cursor.execute("SELECT * FROM student WHERE supervisorID = %s", (supid))
        students = cursor.fetchall()
        cursor.execute("SELECT DISTINCT * FROM application a " + 
                        "LEFT JOIN offer o ON a.offerID = o.offerID " +
                        "LEFT JOIN company c ON o.compID = c.compID")
        offers = cursor.fetchall()

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

    return render_template("SupMyITP.html", students=students, offers = offers)


@app.route("/supervisor/view/report", methods=["GET"])
def view_report():
    filenames = []
    try:
        studid = request.args.get('studid')
        supid = session["userid"]
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT reportID, reportName, dueDate FROM progressReport WHERE supervisorID=%s",
            (supid),
        )
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

    return render_template(
        "SupViewReport.html", classworks=classworks, reports=reports, files=files
    )


@app.route("/supervisor/login", methods=["GET", "POST"])
def sup_login():
    if request.method == "GET":
        return render_template("SupLogin.html", msg="")
    else:
        cursor = db_conn.cursor()
        email = request.form["inputEmail"]
        password = request.form["inputPassword"]
        cursor.execute(
            "SELECT * FROM supervisor WHERE supervisorEmail=%s AND supervisorPassword=%s",
            (email, password),
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


@app.route("/update/report", methods=["GET", "POST"])
def update():
    studid = request.args.get("studid")
    submissionid = request.args.get("submissionid")
    status = request.form["reportStatus"]
    remark = request.form["remark"]
    cursor = db_conn.cursor()

    try:
        cursor.execute(
            "UPDATE submission SET status = %s, remark = %s WHERE submissionID=%s",
            (status, remark, submissionid),
        )
        db_conn.commit()

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

    return redirect(url_for("view_report", studid=studid))


@app.route("/preview/<filename>", methods=["GET"])
def previewFile(filename):
    if request.method == "GET":
        s3 = boto3.resource("s3")
        file = s3.Object(custombucket, filename).get()
        response = make_response(file["Body"].read())
        response.headers["Content-Type"] = "application/pdf"
        return response

@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    if request.method == "GET":
        s3 = boto3.resource("s3")
        output = f"/media/{filename}"
        s3.Bucket(bucket).download_file(Key=filename, Filename=output)
        return send_file(output, as_attachment=True)

@app.route("/admin/compdetails/<compid>", methods=["GET",'POST'])
def CompDetails(compid):
    if request.method == 'GET':
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
        print(contents)
        return render_template('CompDetails.html', comp = compDetails, file = contents)
    elif request.method == 'POST' :
        updateSql = "UPDATE company SET registerStatus=%s where compID=" + compid
        cursor = db_conn.cursor()        
        if request.form.get('reject') == 'reject':
            cursor.execute(updateSql,('Rejected'))
            db_conn.commit()            
            return redirect(url_for("CompRequest"))
        elif request.form.get('approve') == 'approve':
            cursor.execute(updateSql,('Active'))
            db_conn.commit()
            return redirect(url_for("CompRequest"))               
        elif request.form.get('activate') == 'activate':
            cursor.execute(updateSql,('Active'))
            db_conn.commit()             
            return redirect(url_for("RegisteredComp"))            
        elif request.form.get('deactivate') == 'deactivate':
            cursor.execute(updateSql,('Deactivate'))        
            db_conn.commit()              
            return redirect(url_for("RegisteredComp"))

@app.route("/admin/manageoffers", methods=['GET','POST'])
def ManageOffers():
    return render_template("AdminOffers.html")

@app.route("/admin/acceptoffers/<offerid>", methods=['GET','POST'])
def AcceptOffers(offerid):
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE offer SET offerStatus='Active' WHERE offerID=%s",(offerid)
    )
    db_conn.commit()
    cursor.close()    
    return redirect(url_for("ManageOffers"))

@app.route("/admin/rejectoffers/<offerid>", methods=['GET','POST'])
def RejectOffers(offerid):
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE offer SET offerStatus='Rejected' WHERE offerID=%s",(offerid)
    )
    db_conn.commit()
    cursor.close()    
    return redirect(url_for("ManageOffers"))

@app.route("/admin/getpencomp", methods=["POST"])
def Admin_Get_Pending_Comp():
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

            ## Total number of records without filtering
            cursor.execute("SELECT count(*) as allcount from company WHERE registerStatus='Pending'")
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount["allcount"]
            searchValue = "%" + searchValue + "%"
            ## Total number of records with filtering
            cursor.execute(
                "SELECT count(*) as allcount from company WHERE registerStatus='Pending' AND compName LIKE %s",(searchValue))
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute("SELECT * FROM company WHERE registerStatus='Pending' order by registerStatus desc limit %s, %s;",(row, rowperpage))
            else:
                cursor.execute(
                    "SELECT * FROM company WHERE registerStatus='Pending' AND compName LIKE %s order by registerStatus desc limit %s, %s;",(searchValue,row,rowperpage))
            offerlist = cursor.fetchall()
            data = []
            for row in offerlist:
                data.append(
                    {
                        "compID": row["compID"],
                        "compName": row["compName"],
                        "status": row["registerStatus"],
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

@app.route("/admin/getrecomp", methods=["POST"])
def Admin_Get_Resgistered_Comp():
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

            ## Total number of records without filtering
            cursor.execute("SELECT count(*) as allcount from company WHERE registerStatus!='Pending'")
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount["allcount"]
            searchValue = "%" + searchValue + "%"
            ## Total number of records with filtering
            cursor.execute(
                "SELECT count(*) as allcount from company WHERE registerStatus!='Pending' AND compName LIKE %s",(searchValue))
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute("SELECT * FROM company WHERE registerStatus!='Pending' order by registerStatus desc limit %s, %s;",(row, rowperpage))
            else:
                cursor.execute(
                    "SELECT * FROM company WHERE registerStatus!='Pending' AND compName LIKE %s order by registerStatus desc limit %s, %s;",(searchValue,row,rowperpage))
            offerlist = cursor.fetchall()
            data = []
            for row in offerlist:
                data.append(
                    {
                        "compID": row["compID"],
                        "compName": row["compName"],
                        "status": row["registerStatus"],
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

@app.route("/admin/GetAllOffers", methods=["POST"])
def Admin_Get_All_Offers():
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

            ## Total number of records without filtering
            cursor.execute(
                "SELECT count(*) as allcount from offer,company WHERE offerStatus='Pending' AND offer.compID = company.compID")
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount["allcount"]

            ## Total number of records with filtering
            likeString = "%" + searchValue + "%"
            cursor.execute(
                "SELECT count(*) as allcount from offer,company WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s) AND offerStatus='Pending' AND offer.compID = company.compID",
                (likeString, likeString, likeString, likeString, likeString),
            )
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute(
                    "SELECT * FROM offer,company WHERE offerStatus='Pending' AND offer.compID = company.compID ORDER BY offerStatus asc, datePosted desc limit %s, %s;",
                    (row, rowperpage),
                )
                offerlist = cursor.fetchall()
            else:
                cursor.execute(
                    "SELECT * FROM offer,company WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s) AND offerStatus='Pending' AND offer.compID = company.compID ORDER BY offerStatus asc, datePosted desc limit %s, %s;",
                    (
                        likeString,
                        likeString,
                        likeString,
                        likeString,
                        likeString,
                        row,
                        rowperpage,
                    ),
                )
                offerlist = cursor.fetchall()

            data = []
            for row in offerlist:
                print(row["offerID"])
                data.append(
                    {
                        "offerID": row["offerID"],
                        "companyName": row['compName'],
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

@app.route("/admin/Login", methods=["GET", "POST"])
def Admin_Login():
    msg = ""
    cursor = db_conn.cursor()
    if request.method == "POST":
        email = request.form["inputEmail"]
        password = request.form["inputPassword"]
        cursor.execute(
            "SELECT * FROM committee WHERE committeeEmail=%s AND committePassword=%s",
            (email, password),
        )
        record = cursor.fetchone()
        if record:
            session["loggedin"] = True
            session["userid"] = record[0]
            session["username"] = record[1]
            return redirect(url_for("CompRequest"))
        else:
            msg = "Incorrect email/password.Try again!"
    return render_template("AdminLogin.html", msg=msg)

@app.route("/company/login", methods=["GET", "POST"])
def comp_login():
    return render_template("CompLogin.html", msg="")


@app.route("/company/Login", methods=["GET", "POST"])
def Comp_Login():
    msg = ""
    cursor = db_conn.cursor(cursors.DictCursor)
    if request.method == "POST":
        email = request.form["inputEmail"]
        password = request.form["inputPassword"]
        cursor.execute(
            "SELECT * FROM company WHERE compEmail=%s AND compPassword=%s",
            (email, password),
        )
        record = cursor.fetchone()
        if record:
            if record["registerStatus"] == "Active":
                session["loggedin"] = True
                session["userid"] = record["compID"]
                session["username"] = record["compName"]
                flash("Login Successful.", category="Active")
                return redirect(url_for("comp_applications"))
            elif record["registerStatus"] == "Rejected":
                flash("Your Company Registration has been rejected.", category="Rejected")
                return redirect(url_for("comp_login"))
            elif record["registerStatus"] == "Pending":
                flash("Your Company Registration has not been accepted yet.", category="Pending")
                return redirect(url_for("comp_login"))
        else:
            msg = "Incorrect email/password.Try again!"
    return render_template("CompLogin.html", msg=msg)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/previewImg/<file>", methods=["GET"])
def previewImg(file):
    if request.method == "GET":
        s3 = boto3.resource("s3")
        file1 = s3.Object(custombucket, file).get()
    img = file1["Body"].read()
    return send_file(BytesIO(img), mimetype="image/jpeg")
    # return file['Body'].read()


@app.route("/company/applications", methods=["GET", "POST"])
def comp_applications():
    return render_template("CompApplications.html")


@app.route("/company/GetApplications", methods=["POST"])
def Comp_Get_Applications():
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
                "SELECT COUNT(*) AS allcount FROM application a, offer o WHERE a.offerID=o.offerID AND compID=%s",
                compID,
            )
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount["allcount"]

            ## Total number of records with filtering
            likeString = "%" + searchValue + "%"
            cursor.execute(
                "SELECT COUNT(*) AS allcount FROM application a, offer o WHERE (appStatus LIKE %s OR position LIKE %s) AND a.offerID=o.offerID AND compID=%s ORDER BY CASE appStatus WHEN 'Pending' THEN 0 WHEN 'Accepted' THEN 1 WHEN 'Rejected' THEN 2 END ASC, appliedDateTime ASC ;",
                (likeString, likeString, compID),
            )
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute(
                    "SELECT * FROM application a, offer o WHERE a.offerID=o.offerID AND compID=%s ORDER BY CASE appStatus WHEN 'Pending' THEN 0 WHEN 'Accepted' THEN 1 WHEN 'Rejected' THEN 2 END ASC, appliedDateTime ASC LIMIT %s, %s;",
                    (compID, row, rowperpage),
                )
                offerlist = cursor.fetchall()
            else:
                cursor.execute(
                    "SELECT * FROM application a, offer o WHERE (appStatus LIKE %s OR position LIKE %s) AND a.offerID=o.offerID AND compID=%s ORDER BY CASE appStatus WHEN 'Pending' THEN 0 WHEN 'Accepted' THEN 1 WHEN 'Rejected' THEN 2 END ASC, appliedDateTime ASC LIMIT %s, %s;",
                    (likeString, likeString, compID, row, rowperpage),
                )
                offerlist = cursor.fetchall()

            data = []
            for row in offerlist:
                data.append(
                    {
                        "appID": row["appID"],
                        "appStatus": row["appStatus"],
                        "appliedDateTime": row["appliedDateTime"].strftime("%d-%m-%Y"),
                        "position": row["position"],
                        "allowance": row["allowance"],
                        "duration": row["duration"],
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
                "SELECT count(*) as allcount from offer WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s OR offerStatus LIKE %s) AND compID=%s",
                (
                    likeString,
                    likeString,
                    likeString,
                    likeString,
                    likeString,
                    likeString,
                    compID,
                ),
            )
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute(
                    "SELECT * FROM offer WHERE compID=%s ORDER BY CASE offerStatus WHEN 'Pending' THEN 0 WHEN 'Active' THEN 1 WHEN 'Revoked' THEN 2 WHEN 'Rejected' THEN 3 END ASC, datePosted DESC limit %s, %s;",
                    (compID, row, rowperpage),
                )
                offerlist = cursor.fetchall()
            else:
                cursor.execute(
                    "SELECT * FROM offer WHERE (position LIKE %s OR location LIKE %s OR prerequisite LIKE %s OR language LIKE %s OR allowance LIKE %s OR offerStatus LIKE %s) AND compID=%s ORDER BY CASE offerStatus WHEN 'Pending' THEN 0 WHEN 'Active' THEN 1 WHEN 'Revoked' THEN 2 WHEN 'Rejected' THEN 3 END ASC, datePosted DESC limit %s, %s;",
                    (
                        likeString,
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


@app.route("/company/UpdateOfferDetails", methods=["GET", "POST"])
def comp_update_offer_details():
    offerID = request.form["inputOfferID"]
    offerStatus = request.form["inputOfferStatus"]
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE offer SET offerStatus = %s WHERE offerID=%s;",
        (offerStatus, offerID),
    )
    db_conn.commit()
    cursor.close()
    return redirect(url_for("comp_offer_details", id=offerID))


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
                "SELECT COUNT(*) AS allcount FROM application WHERE appStatus LIKE %s AND offerID=%s ORDER BY CASE appStatus WHEN 'Pending' THEN 0 WHEN 'Accepted' THEN 1 WHEN 'Rejected' THEN 2 END ASC, appliedDateTime ASC;",
                (likeString, offerID),
            )
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount["allcount"]

            ## Fetch records
            if searchValue == "":
                cursor.execute(
                    "SELECT * FROM application a, student s WHERE a.studID=s.studID AND offerID=%s ORDER BY CASE appStatus WHEN 'Pending' THEN 0 WHEN 'Accepted' THEN 1 WHEN 'Rejected' THEN 2 END ASC, appliedDateTime ASC LIMIT %s, %s;",
                    (offerID, row, rowperpage),
                )
                offerlist = cursor.fetchall()
            else:
                cursor.execute(
                    "SELECT * FROM application a, student s WHERE a.studID=s.studID AND appStatus LIKE %s AND offerID=%s ORDER BY CASE appStatus WHEN 'Pending' THEN 0 WHEN 'Accepted' THEN 1 WHEN 'Rejected' THEN 2 END ASC, appliedDateTime ASC LIMIT %s, %s;",
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
    appID = request.args.get("appid")
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
            if file.startswith("stud-id-" + record["studID"] + "_resume"):
                contents.append(file)
        return render_template(
            "CompApplicationDetails.html", appdetails=record, file=contents
        )
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        db_conn2.close()


@app.route("/company/RespondApplication", methods=["GET", "POST"])
def comp_respond_app():
    offerID = request.form["inputOfferID"]
    appID = request.form["inputAppID"]
    appStatus = request.form["inputAppStatus"]
    feedback = request.form["inputFeedback"]
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE application SET appStatus = %s, feedback=%s WHERE appID=%s;",
        (appStatus, feedback, appID),
    )
    db_conn.commit()
    cursor.close()
    return redirect(url_for("comp_app_details", offerid=offerID, appid=appID))


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
    datePosted = datetime.datetime.now()
    offerStatus = "Pending"
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


@app.route("/student/studRegisterPage", methods=['GET','POST'])
def stud_register_page():

    try:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT supervisorName FROM supervisor")
        supervisors = cursor.fetchall()
        print(supervisors)

    except Exception as e:
            print(e)
            return str(e)

    finally:
        cursor.close()

    return render_template('RegisterStudent.html', supervisors=supervisors)

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
        cursor.execute("SELECT supervisorName FROM supervisor")
        supervisors = cursor.fetchall()

    except Exception as e:
            return str(e)

    finally:
        cursor.close()

    return render_template('StudentDetails.html', studDetails=studDetails, msg=msg, supervisors=supervisors)

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
    # msg = request.args.get("msg")
    # if msg is None:
    #     msg = ''

    return render_template('StudUploadDoc.html')

@app.route("/student/uploadDoc", methods=['GET','POST'])
def stud_uploadDoc():
    if request.method == "POST":

        studID = session["userid"]

        companyAcceptanceLetter = request.files["inputCompanyAcceptanceLetter"]
        letterOfIdemnity = request.files["inputLetterOfIdemnity"]
        acknowledgeForm = request.files["inputAcknowledgeForm"]
        
        if companyAcceptanceLetter.filename == "":
            return "Please upload your company acceptance letter!"
        
        if letterOfIdemnity.filename == "":
            return "Please upload your letter of idemnity!"
        
        if acknowledgeForm.filename == "":
            return "Please upload your parent's acknoledgement form!"


        companyAcceptanceLetter_file = "stud-id-" + str(studID) + "_CAL.pdf"
        letterOfIdemnity_file = "stud-id-" + str(studID) + "_LOI.pdf"
        acknowledgeForm_file = "stud-id-" + str(studID) + "_AF.pdf"
        s3 = boto3.resource("s3")

        # msg = "Documents uploaded."

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
        
        except Exception as e:
            return str(e)

    stud_viewDoc_page
    return redirect(url_for("stud_viewDoc_page"))

@app.route("/portfolio", methods=['GET','POST'])
def portfolio_page():
    return render_template('Portfolio.html')

@app.route("/portfolio/qs")
def qs_page():
    return render_template('WQS.html')

@app.route("/portfolio/je")
def je_page():
    return render_template('LJE.html')

@app.route("/portfolio/kw")
def kw_page():
    return render_template('HKW.html')

@app.route("/portfolio/amos")
def amos_page():
    return render_template('AMOS.html')


@app.route("/stud/submission")
def stud_submission():
    filenames = []

    try:
        studid = session['userid']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM student s, progressReport p WHERE s.supervisorID = "
                       + "p.supervisorID AND studID = %s", (studid))  
        classworks = cursor.fetchall()
        cursor.execute("SELECT * FROM submission WHERE studID = %s", (studid))
        submissions = cursor.fetchall()

        # get filename
        for report in classworks:
            filenames.append("report_" + str(report['reportID']) + "_" + str(report['studName']) + "_" + str(report['studID']) + ".pdf")

        files = list_files(filenames)
        # print(files)
    
    except Exception as e:
        return str(e)
    
    finally:
        cursor.close()

    return render_template("StudSubmitReport.html", classworks=classworks, submissions=submissions, files=files)

@app.route("/stud/submit/<reportid>", methods=["GET", "POST"])
def submit(reportid):
    pdf = request.files["inputPdf"]
    studid = session['userid']
    studName = session['username']
    cursor = db_conn.cursor(cursors.DictCursor)
    handInDate = datetime.datetime.now()
    filenames = []

    if pdf.filename == "":
        return "Please select a pdf to submit"

    try:
        cursor.execute("INSERT INTO submission (handInDate, reportID, studID) VALUES (%s, %s, %s)", (handInDate, reportid, str(studid)))
        db_conn.commit()
        cursor.execute("SELECT * FROM student WHERE studID = %s", (str(studid)))  
        student = cursor.fetchone()

        filenames.append("report_" + str(reportid) + "_" + str(student['studName']) + "_" + str(student['studID']) + ".pdf")
        
        # Uplaod image file in S3 #
        report_file = "report_" + str(reportid) + "_" + str(student['studName']) + "_" + str(student['studID']) + ".pdf"
        s3 = boto3.resource("s3")

        print("Data inserted in MySQL RDS... uploading image to S3...")
        s3.Bucket(custombucket).put_object(Key=report_file, Body=pdf, ContentType="application/pdf")
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
    studid = session['userid']
    name = session['username']
    cursor = db_conn.cursor()

    try:
        cursor.execute("DELETE FROM submission WHERE reportID=%s AND studID=%s", (reportid, studid))
        db_conn.commit()
        
        # Delete image file in S3 #
        print("Data deleted in MySQL RDS... deleteing image from S3...")
        report_file = "report_" + str(reportid) + "_" + name + "_" + studid + ".pdf"
        s3 = boto3.resource("s3")
        s3.Object(custombucket, report_file).delete()

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
