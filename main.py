from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from app import fetchFile, checkFilePresent, downloadFromSupabase, pastPaperChecker, segmentAnswerScript, uploadToSupabase, signInUser, signUpUser, insertGradingHistory
import io, os, uuid
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

secretKey = os.getenv("FLASK_SECRET_KEY")

if not secretKey:
    raise RuntimeError("FLASK_SECRET_KEY must be set in your .env file")

app.secret_key = secretKey

def loginRequired(routeFunc):
    @wraps(routeFunc)
    def wrappedFunc(*args, **kwargs):
        if "userId" not in session:
            return redirect(url_for("loginPage"))
        return routeFunc(*args, **kwargs)
    return wrappedFunc

@app.route("/")
def homePage():
    return render_template("home.html")

@app.route("/fetch-file", methods = ["GET", "POST"])
def fetchFilePage():
    if request.method == "GET":
        return render_template("fetchFile.html")

    subjectName = request.form.get("subjectName")
    subjectCode = request.form.get("subjectCode")
    examinationYear = request.form.get("examinationYear")
    examinationSeries = request.form.get("examinationSeries")
    variant = request.form.get("variant")
    fileType = request.form.get("fileType")

    if not all([subjectName, subjectCode, examinationSeries, examinationYear, variant, fileType]):
        return render_template("fetchFile.html", error="All fields are required.")

    assert subjectName is not None
    assert subjectCode is not None
    assert examinationYear is not None
    assert examinationSeries is not None
    assert variant is not None
    assert fileType is not None

    lastTwoDigits = str(int(examinationYear))[-2:]

    if examinationSeries == "may-june":
        shortenedCodeKey = "s"
    else:
        shortenedCodeKey = "w"

    shortenedCode = shortenedCodeKey + lastTwoDigits

    fileStatus, result = checkFilePresent(subjectName, subjectCode, examinationYear, examinationSeries, shortenedCode, variant, fileType)

    if not fileStatus:
        fetchStatus, fetchResult = fetchFile(subjectName, subjectCode, examinationYear, examinationSeries, shortenedCode, variant, fileType)

        if not fetchStatus:
            return render_template("fetchFile.html", error=f"Failed to download file: {fetchResult}")

        result = fetchResult

    downloadStatus, fileBytes = downloadFromSupabase("papers", result)

    if not downloadStatus:
        return render_template("fetchFile.html", error=f"Failed to retrieve file from storage: {fileBytes}")

    assert isinstance(fileBytes, bytes)
    assert isinstance(result, str)

    downloadFileName = os.path.basename(result)

    return send_file(
        io.BytesIO(fileBytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=downloadFileName
    )

@app.route("/past-paper-checker")
@loginRequired
def pastPaperCheckerPage():
    return render_template("pastPaperChecker.html")

@app.route("/past-paper-checker/submit", methods = ['POST'])
@loginRequired
def pastPaperCheckerSubmit():
    subjectName = request.form.get("subjectName")
    subjectCode = request.form.get("subjectCode")
    examYear = request.form.get("examinationYear")
    examSeries = request.form.get("examinationSeries")
    variant = request.form.get("variant")
    questionScope = request.form.get("questionScope")
    questionNumber = request.form.get("questionNumber")
    uploadedFiles = request.files.getlist("answerImages")

    if not all([subjectName, subjectCode, examYear, examSeries, variant, questionScope]):
        return render_template("pastPaperChecker.html", error="All fields are required.")

    assert subjectName is not None
    assert subjectCode is not None
    assert examYear is not None
    assert examSeries is not None
    assert variant is not None
    assert questionScope is not None

    if questionScope == "specific" and not questionNumber:
        return render_template("pastPaperChecker.html", error="Please enter a question number.")


    if not uploadedFiles:
        return render_template("pastPaperChecker.html", error="Please upload at least one answer image.")

    lastTwoDigits = str(int(examYear))[-2:]

    if examSeries == "may-june":
        shortenedCodeKey = "s"
    else:
        shortenedCodeKey = "w"

    shortenedCode =shortenedCodeKey + lastTwoDigits

    markSchemeStatus, markSchemePath = checkFilePresent(subjectName, subjectCode, examYear, examSeries, shortenedCode, variant, "ms")

    if not markSchemeStatus:
        fetchStatus, fetchResult = fetchFile(subjectName, subjectCode, examYear, examSeries, shortenedCode, variant, fileType="ms")

        if not fetchStatus:
            return render_template("pastPaperChecker.html", error=f"Failed to fetch mark scheme: {fetchResult}")

        markSchemePath = fetchResult

    assert isinstance(markSchemePath, str)

    requestId = str(uuid.uuid4())
    uploadedImagePaths = []

    for uploadedFile in uploadedFiles:
        destinationPath = f"{requestId}/{uploadedFile.filename}"
        uploadStatus, uploadResult = uploadToSupabase("answer-uploads", destinationPath, uploadedFile.read(), uploadedFile.mimetype or "image/jpeg")

        if not uploadStatus:
            return render_template("pastPaperChecker.html", error=f"Failed to upload image {uploadedFile.filename}: {uploadResult}")

        uploadedImagePaths.append(uploadResult)

    if questionScope == "specific":
        gradeStatus, gradeResult = pastPaperChecker(subjectName, subjectCode, examYear, examSeries, variant, questionNumber, markSchemePath, uploadedImagePaths)

        if not gradeStatus:
            return render_template("pastPaperChecker.html", error=f"Grading Failed: {gradeResult}")

        assert isinstance(gradeResult, dict)

        historyStatus, historyError = insertGradingHistory(session["userId"], subjectName, subjectCode, examYear, examSeries, variant, questionNumber, gradeResult)

        if not historyStatus:
            print(f"Failed to insert grading history: {historyError}")
        
        return render_template("pastPaperChecker.html", result=gradeResult)

    segmentStatus, segmentResult = segmentAnswerScript(uploadedImagePaths)

    if not segmentStatus:
        return render_template("pastPaperChecker.html", error=f"Segmentation Failed: {segmentResult}")

    assert isinstance(segmentResult, dict)

    return jsonify({
        "status": True,
        "segments": segmentResult["segments"],
        "unmatchedImageIndices": segmentResult.get("unmatched_image_indices", []),
        "imagePaths": uploadedImagePaths,
        "markSchemePath": markSchemePath,
        "subjectName": subjectName,
        "subjectCode": subjectCode,
        "examinationYear": examYear,
        "examinationSeries": examSeries,
        "variant": variant
    })

@app.route("/api/grade-question", methods = ["POST"])
@loginRequired
def apiGradeQuestion():
    data = request.get_json()

    if not data:
        return jsonify({
            "status": False,
            "result": "No JSON Data Provided."
        }), 400

    requiredFields = [
        "subjectName",
        "subjectCode",
        "examinationYear",
        "examinationSeries",
        "variant",
        "questionNumber",
        "markSchemePath",
        "answerImagesPath"
    ]

    for field in requiredFields:
        if field not in data:
            return jsonify({
                "status": False,
                "result": f"Missing Required Field: {field}"
            }), 400

    gradeStatus, gradeResult = pastPaperChecker(
        data["subjectName"],
        data["subjectCode"],
        data["examinationYear"],
        data["examinationSeries"],
        data["variant"],
        data["questionNumber"],
        data["markSchemePath"],
        data["answerImagesPath"]
    )

    if gradeStatus:
        assert isinstance(gradeResult, dict)
        historyStatus, historyError = insertGradingHistory(
            session["userId"],
            data["subjectName"],
            data["subjectCode"],
            data["examinationYear"],
            data["examinationSeries"],
            data["variant"],
            data["questionNumber"],
            gradeResult
        )

        if not historyStatus:
            print(f"Failed to insert grading history: {historyError}")

    return jsonify(
        {
            "status": gradeStatus,
            "result": gradeResult
        }
    )

@app.route("/signup", methods=["GET", "POST"])
def signUpPage():
    if request.method == "GET":
        return render_template("signup.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return render_template("signup.html", error="Email and Password are both required.")

    signUpStatus, signUpResult = signUpUser(email, password)

    if not signUpStatus:
        return render_template("signup.html", error=signUpResult)

    assert isinstance(signUpResult, dict)

    session["userId"] = signUpResult["userId"]
    session["userEmail"] = email

    return redirect(url_for("homePage"))

@app.route("/login", methods=["GET", "POST"])
def loginPage():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return render_template("login.html", error="Email and Password are both required.")

    signInStatus, signInResult = signInUser(email, password)

    if not signInStatus:
        return render_template("login.html", error=signInResult)

    assert isinstance(signInResult, dict)

    session["userId"] = signInResult["userId"]
    session["userEmail"] = email

    return redirect(url_for("homePage"))

@app.route("/logout", methods=["POST"])
def logoutRoute():
    session.clear()
    return redirect(url_for("homePage"))

if __name__ == "__main__":
    app.run(debug=True)