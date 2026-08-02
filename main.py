from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from app import fetchFile, checkFilePresent, downloadFromSupabase, pastPaperChecker, segmentAnswerScript, uploadToSupabase, signInUser, signUpUser, insertGradingHistory, getGradingHistory, getChatHistory, coachChat, getWeakTopics, getGradingHistoryEntry, genFlashCardsFromResult, getDueFlashCards, reviewFlashcard, genProgressRepPdf, genPracticeQuestions, getPracticeQuestions, getPracticeQuestionEntry, gradeTypedAnswer
import io, os, uuid
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv(override=True)

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
        return jsonify(
            {
                "status": False,
                "result": "All fields are required."
            }
        )

    assert subjectName is not None
    assert subjectCode is not None
    assert examYear is not None
    assert examSeries is not None
    assert variant is not None
    assert questionScope is not None

    if questionScope == "specific" and not questionNumber:
        return jsonify(
            {
                "status": False,
                "result": "Please enter a question number."
            }
        )


    if not uploadedFiles:
        return jsonify(
            {
                "status": False,
                "result": "Please upload at least one answer image."
            }
        )

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
            return jsonify(
                {
                    "status": False,
                    "result": f"Failed to fetch mark scheme: {fetchResult}"
                }
            )

        markSchemePath = fetchResult

    assert isinstance(markSchemePath, str)

    requestId = str(uuid.uuid4())
    uploadedImagePaths = []

    for uploadedFile in uploadedFiles:
        destinationPath = f"{requestId}/{uploadedFile.filename}"
        uploadStatus, uploadResult = uploadToSupabase("answer-uploads", destinationPath, uploadedFile.read(), uploadedFile.mimetype or "image/jpeg")

        if not uploadStatus:
            return jsonify(
                {
                    "status": False,
                    "result": f"Failed to upload answer image {uploadedFile.filename}: {uploadResult}"
                }
            )

        uploadedImagePaths.append(uploadResult)

    if questionScope == "specific":
        gradeStatus, gradeResult = pastPaperChecker(subjectName, subjectCode, examYear, examSeries, variant, questionNumber, markSchemePath, uploadedImagePaths)

        if not gradeStatus:
            return jsonify(
                {
                    "status": False,
                    "result": f"Grading Failed: {gradeResult}"
                }
            )

        assert isinstance(gradeResult, dict)

        historyStatus, historyResult = insertGradingHistory(session["userId"], subjectName, subjectCode, examYear, examSeries, variant, questionNumber, gradeResult)

        if not historyStatus:
            print(f"Failed to insert grading history: {historyResult}")
        else:
            genFlashCardsFromResult(session["userId"], subjectName, gradeResult.get("topic"), historyResult, gradeResult)
        
        return jsonify(
            {
                "status": True,
                "mode": "specific",
                "result": gradeResult,
                "historyEntryId": historyResult if historyStatus else None
            }
        )

    segmentStatus, segmentResult = segmentAnswerScript(uploadedImagePaths)

    if not segmentStatus:
        return jsonify(
            {
                "status": False,
                "result": f"Segmentation Failed: {segmentResult}"
            }
        )

    assert isinstance(segmentResult, dict)

    return jsonify({
        "status": True,
        "mode": "all",
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
        historyStatus, historyResult = insertGradingHistory(
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
            print(f"Failed to insert grading history: {historyResult}")
        else:
            genFlashCardsFromResult(session["userId"], data["subjectName"], gradeResult.get("topic"), historyResult, gradeResult)

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

@app.route("/grading-history")
@loginRequired
def gradingHistoryPage():
    historyStatus, historyData = getGradingHistory(session["userId"])

    if not historyStatus:
        return render_template("gradingHistory.html", error=f"Failed to load grading history: {historyData}")

    assert isinstance(historyData, list)

    return render_template("gradingHistory.html", history=historyData)

@app.route("/weak-topics")
@loginRequired
def weakTopicsPage():
    topicStatus, topicsData = getWeakTopics(session["userId"])

    if not topicStatus:
        return render_template("weakTopics.html", error=f"Failed to load topic analysis: {topicsData}")

    return render_template("weakTopics.html", topics=topicsData)

@app.route("/progress-report")
@loginRequired
def progressReportDownload():
    pdfStatus, pdfResult = genProgressRepPdf(session["userId"], session["userEmail"])

    if not pdfStatus:
        return render_template("weakTopics.html", error=f"Failed to generate report: {[pdfResult]}")

    assert isinstance(pdfResult, bytes)

    return send_file(
        io.BytesIO(pdfResult),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="OLeveliPy_Progress_Report.pdf"
    )

@app.route("/flashcards")
@loginRequired
def flashCardsPage():
    dueStatus, dueCards = getDueFlashCards(session["userId"])

    if not dueStatus:
        return render_template("flashcards.html", error=f"Failed to load flashcards: {dueCards}", cards=[])

    return render_template("flashcards.html", cards=dueCards)

@app.route("/api/review-flashcard", methods=["POST"])
@loginRequired
def apiReviewFlashcard():
    data = request.get_json()

    if not data or "flashcardId" not in data or "quality" not in data:
        return jsonify(
            {
                "status": False,
                "result": "Missing Flashcard ID or Quality."
            }
        ), 400

    reviewStatus, reviewErr = reviewFlashcard(session["userId"], data["flashcardId"], int(data["quality"]))

    return jsonify(
        {
            "status": reviewStatus,
            "result": reviewErr
        }
    )

@app.route("/practice-questions")
@loginRequired
def practiceQuestionsPage():
    listStatus, listData = getPracticeQuestions(session["userId"])

    if not listStatus:
        return render_template("practiceQuestions.html", error=f"Failed to load practice questions: {listData}", questions=[])

    return render_template("practiceQuestions.html", questions=listData)

@app.route("/api/generate-practice-question", methods=["POST"])
@loginRequired
def apiGenPracticeQuestion():
    data = request.get_json()

    if not data or not data.get("subjectName") or not data.get("topic"):
        return jsonify(
            {
                "status": False,
                "result": "Subject Name and Topic are Required!"
            }
        ), 400

    genStatus, genResult = genPracticeQuestions(session["userId"], data["subjectName"], data["topic"])

    return jsonify(
        {
            "status": genStatus,
            "result": genResult
        }
    )

@app.route("/api/grade-practice-question", methods=["POST"])
@loginRequired
def apiGradePracticeQuestion():
    questionId = request.form.get("questionId")
    answerText = request.form.get("answerText")
    uploadedFiles = request.files.getlist("answerImages")

    if not questionId:
        return jsonify(
            {
                "status": False,
                "result": "Missing Question ID"
            }
        ), 400

    if not uploadedFiles and not answerText:
        return jsonify(
            {
                "status": False,
                "result": "Please upload at least one answer image or type the answer."
            }
        ), 400

    entryStatus, entryData = getPracticeQuestionEntry(session["userId"], questionId)

    if not entryStatus:
        return jsonify(
            {
                "status": False,
                "result": entryData
            }
        )

    assert isinstance(entryData, dict)

    if answerText and answerText.strip():
        gradeStatus, gradeResult = gradeTypedAnswer(
            entryData["subject_name"],
            "Generated",
            str(date.today().year),
            "Practice",
            "1",
            "1",
            entryData["mark_scheme_path"],
            answerText
        )
    else:
        requestId = str(uuid.uuid4())
        uploadedImagePaths = []

        for uploadedFile in uploadedFiles:
            path = f"{requestId}/{uploadedFile.filename}"
            uploadStatus, uploadResult = uploadToSupabase("answer-uploads", path, uploadedFile.read(), uploadedFile.mimetype or "image/jpeg")

            if not uploadStatus:
                return jsonify(
                    {
                        "status": False,
                        "result": f"Failed to upload answer image: {uploadResult}"
                    }
                )

            uploadedImagePaths.append(uploadResult)

        gradeStatus, gradeResult = pastPaperChecker(
            entryData["subject_name"],
            "Generated",
            str(date.today().year),
            "Practice",
            "1",
            "1",
            entryData["mark_scheme_path"],
            uploadedImagePaths
        )

    if gradeStatus:
        assert isinstance(gradeResult, dict)

        historyStatus, historyResutl = insertGradingHistory(
            session["userId"], entryData["subject_name"], "Generated", str(date.today().year), "Practice", "1", "1", gradeResult
        )

        if historyStatus:
            genFlashCardsFromResult(session["userId"], entryData["subject_name"], gradeResult.get("topic"), historyResutl, gradeResult)

    return jsonify(
        {
            "status": gradeStatus,
            "result": gradeResult
        }
    )

@app.route("/coach-chat")
@loginRequired
def coachChatPage():
    chatStatus, chatHistoryData = getChatHistory(session["userId"])

    if not chatStatus:
        chatHistoryData = []

    aboutEntryId = request.args.get("about")
    preFillMsg = None

    if aboutEntryId:
        entryStatus, entryData = getGradingHistoryEntry(session["userId"], aboutEntryId)

        if entryStatus:
            assert isinstance(entryData, dict)
            marksAwarded = entryData.get("marks_awarded")
            marksTotal = entryData.get("marks_total")

            examDesc = f"{entryData.get('subject_name')} {entryData.get('examination_year')} {entryData.get('examination_series')} question {entryData.get('question_number')}"

            if marksAwarded is not None and marksTotal is not None and marksAwarded >= marksTotal:
                preFillMsg = f"Can you please review my answer on {examDesc} (scored full marks, {marksAwarded}/{marksTotal}) and lemme know if there's anything I could do even better next time?"
            else:
                preFillMsg = f"Can you please help me understand what I got wrong on {examDesc} (scored {marksAwarded}/{marksTotal})?"
    return render_template("coachChat.html", chatHistory=chatHistoryData, aboutEntryId=aboutEntryId, prefillMessage=preFillMsg)

@app.route("/api/coach-chat", methods=["POST"])
@loginRequired
def apiCoachChat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify(
            {
                "status": False,
                "result": "No Input Message Provided :("
            }
        ), 400

    chatStatus, chatResult = coachChat(session["userId"], data["message"], data.get('aboutEntryId'))

    return jsonify(
        {
            "status": chatStatus,
            "result": chatResult
        }
    )

if __name__ == "__main__":
    app.run(debug=True)