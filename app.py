from flask import Flask, render_template, request, redirect, url_for, send_file, session,  jsonify, json
from pymysql import connections, cursors
import os
import boto3
from config import *
from io import BytesIO

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
        return render_template('CompDetails.html', comp = compDetails, file = 'test')
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

@app.route("/admin/registredcomp", methods=['GET','POST'])
def RegisteredComp():
    return render_template("RegisteredComp.html")

@app.route("/admin/compregistration", methods=['GET','POST'])
def CompRequest():
    return render_template("CompRegistration.html")

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
        file1 = s3.Object(custombucket, file).get()
    img = file1['Body'].read()
    return send_file(BytesIO(img), mimetype='image/jpeg')

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
