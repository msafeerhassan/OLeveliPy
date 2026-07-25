from flask import Flask, render_template, request, jsonify, send_file
from app import fetchFile, checkFilePresent, downloadFromSupabase
import io, os

app = Flask(__name__)

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
def pastPaperCheckerPage():
    return "Past Paper Checker Page :)"

@app.route("/past-paper-checker/submit", methods = ['POST'])
def pastPaperCheckerSubmit():
    return jsonify(
        {
            "status": "nothing"
        }
    )

@app.route("/api/grade-question", methods = ["POST"])
def apiGradeQuestion():
    return jsonify(
        {
            "status": "everything"
        }
    )

if __name__ == "__main__":
    app.run(debug=True)