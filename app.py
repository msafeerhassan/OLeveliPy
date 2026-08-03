import requests, os, base64, json, time, uuid
from typing import Any
from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions
from dotenv import load_dotenv
from PIL import Image
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from datetime import date, timedelta

load_dotenv(override=True)

aiModel = "google/gemini-3.1-flash-lite"

supabaseUrl = os.getenv("SUPABASE_URL")
supabaseKey = os.getenv("SERVICE_ROLE_KEY")
aiKey = os.getenv("HCAI_KEY")

if not supabaseUrl or not supabaseKey:
    raise RuntimeError("SUPABASE_URL and SERVICE_ROLE_KEY must be set in your environment variables file (.env)")

print(f"Debugging: Loaded Supabase url: {supabaseUrl}")
print(f"Debugging: loaded service role key length = {len(supabaseKey)}, starts with {supabaseKey[:6]} and ends with {supabaseKey[-6:]}")

supabase: Client = create_client(supabaseUrl, supabaseKey, options=SyncClientOptions(storage_client_timeout=60))
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def uploadToSupabase(bucketName, destinationPath, fileBytes, contentType, maxRetries=3):
    lastError = "Unknown Error"

    for attempt in range(maxRetries):
        try:
            supabase.storage.from_(bucketName).upload(
                path=destinationPath,
                file=fileBytes,
                file_options={
                    "content-type": contentType,
                    "upsert":"true"
                }
            )

            return True, destinationPath
        except Exception as e:
            lastError = str(e)
            if attempt < maxRetries - 1:
                time.sleep(2 ** attempt)

    return False, lastError

def downloadFromSupabase(bucketName, filePath, maxRetries=3):
    lastError = "Unknow Error"

    for attempt in range(maxRetries):
        try:
            fileBytes = supabase.storage.from_(bucketName).download(filePath)
            return True, fileBytes
        except Exception as e:
            lastError = str(e)
            if attempt < maxRetries - 1:
                time.sleep(2 ** attempt)

    return False, lastError

def checkExistInSupabase(bucketName, filePath):
    try:
        folderPath = os.path.dirname(filePath)
        fileName = os.path.basename(filePath)

        fileList = supabase.storage.from_(bucketName).list(folderPath)

        for file in fileList:
            if file["name"] == fileName:
                return True

        return False
    except Exception as e:
        return False

def fetchFile(subjectName: str, subjectCode, examinationYear, examinationSeries:str, shortenedCode:str, variant, fileType="ms"):
    subjectNameFormatted = subjectName.lower()
    subjectCodeFormatted = int(subjectCode)
    examinationYearFormatted = int(examinationYear)
    examinationSeriesFormatted = examinationSeries.lower()
    shortenedCodeFormatted = shortenedCode.lower()
    fileTypeFormatted = fileType.lower()
    variantFormatted = int(variant)

    baseUrl = f"https://xtrapapers.co/papers/caie/o-level/{subjectNameFormatted}-{subjectCodeFormatted}/{examinationYearFormatted}-{examinationSeriesFormatted}/{subjectCodeFormatted}_{shortenedCodeFormatted}_{fileTypeFormatted}_{variantFormatted}.pdf"

    fileName = f"{subjectNameFormatted}_{subjectCodeFormatted}_{examinationYearFormatted}_{examinationSeriesFormatted}_{shortenedCodeFormatted}_{variantFormatted}_{fileTypeFormatted}.pdf"

    downloadUrl = f"{baseUrl}/download"

    storagePath = f"{fileTypeFormatted}/{fileName}"

    lastError = "Unknown Error"
    response = None


    for attempt in range(3):
        try:
            response = requests.get(downloadUrl, headers=headers, timeout=30)
            response.raise_for_status()
            break
        except Exception as e:
            lastError = str(e)
            response = None

            if attempt < 2:
                time.sleep(2 ** attempt)

    if response is None:
        return False, lastError

    uploadStatus, uploadResult = uploadToSupabase("papers", storagePath, response.content, "application/pdf")

    if not uploadStatus:
        return False, uploadResult

    return True, storagePath

def checkFilePresent(subjectName: str, subjectCode, examinationYear, examinationSeries:str, shortenedCode:str, variant, fileType="ms"):
    subjectNameFormatted = subjectName.lower()
    subjectCodeFormatted = int(subjectCode)
    examinationYearFormatted = int(examinationYear)
    examinationSeriesFormatted = examinationSeries.lower()
    shortenedCodeFormatted = shortenedCode.lower()
    fileTypeFormatted = fileType.lower()
    variantFormatted = int(variant)

    targetFileName = f"{subjectNameFormatted}_{subjectCodeFormatted}_{examinationYearFormatted}_{examinationSeriesFormatted}_{shortenedCodeFormatted}_{variantFormatted}_{fileTypeFormatted}.pdf"

    storagePath = f"{fileTypeFormatted}/{targetFileName}"

    exists = checkExistInSupabase("papers", storagePath)

    if exists:
        return True, storagePath

    return False, None

def compressImageBytes(imageBytes: bytes, maxDimension=1600, quality=85):
    image = Image.open(io.BytesIO(imageBytes))

    if image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail((maxDimension, maxDimension))

    outputBuff = io.BytesIO()
    image.save(outputBuff, format="JPEG", quality=quality)

    return outputBuff.getvalue()

def encodeBytesToBase64Uri(fileBytes: bytes, mimeType: str):
    encodedData = base64.b64encode(fileBytes).decode("utf-8")

    return f"data:{mimeType};base64,{encodedData}"

def pastPaperChecker(subjectName, subjectCode, examinationYear, examinationSeries, variant, questionNumber, markSchemePath, answerImagesPath):
    if not aiKey:
        return False, "Hack Club AI API Key Missing :("

    if not answerImagesPath:
        return False, "No Answer Images Provided :("

    markSchemeDownloadStatus, markSchemeBytes = downloadFromSupabase("papers", markSchemePath)

    if not markSchemeDownloadStatus:
        return False, f"Failed to download mark scheme from storage: {markSchemeBytes}"

    assert isinstance(markSchemeBytes, bytes)

    markSchemeEncoded = encodeBytesToBase64Uri(markSchemeBytes, "application/pdf")

    answerImagesEncodedArr = []

    for imagePath in answerImagesPath:
        imageDownloadStatus, imageBytes = downloadFromSupabase("answer-uploads", imagePath)

        if not imageDownloadStatus:
            return False, f"Failed to download answer image '{imagePath}' from storage: {imageBytes}"

        assert isinstance(imageBytes, bytes)

        compressedImageBytes = compressImageBytes(imageBytes)

        answerImageEncoded = encodeBytesToBase64Uri(compressedImageBytes, "image/jpeg")

        answerImagesEncodedArr.append(answerImageEncoded)

    SYSTEM_PROMPT = f"""
You are an experienced {subjectName} examiner grading a student's handwritten answer for CAIE O Level Exam ({subjectName}, code {subjectCode}, {examinationYear} {examinationSeries}, variant {variant}).
    You will be given:
    1. The official mark scheme PDF For that full paper.
    2. One or more images of student's handwritten answer to Question {questionNumber} (multiple images means multiple pages of same answer, in proper order).

    Your Task:
    1. Transcribe Exactly what the student has written across all provided images, in order. If any part is illegible, say so explicitly rather than guessing.
    2. Confirm the question number the answer is actually addressing, based on what's visible in the images. If it doesn't match {questionNumber}, note this clearly in your output but still grade against question {questionNumber}'s mark scheme, since that is what was was requested.
    3. Locate question {questionNumber} in the mark scheme and identify each individual mark scheme point (each thing that earns credit) and maximum marks available.
    4. Compared the transcribed answer against each mark scheme point and decide whether it was met, partially met or missed with bried reasoning for each.
    5. Sum the marks awarded.

    Also, read other general instructions mentioned regarding checking paper in the mark scheme.

    Also, identify the specific {subjectName} topic the question texts (e.g. "Momentum", "Electricity", "Waves", "Nervous System", "Alkanes"). Use a consistent standard O Level topic name, not an overly specific or one-off description.

    Respond with ONLY a single valid JSON object, no mark down code fence, no preamble, no explaination outside the JSON. Use exactly this structure:
    {{
        "question_number_requested": "{questionNumber}",
        "question_number_detected_in_image": "<question number you acutally see written, or null if unclear>",
        "question_number_mismatch_warning": "<null or a short note if detected number differs from requested>",
        "topic": "<standard topic name for this question>",
        "transcription": "<full transcription of the handwritten answer>",
        "illegible_sections": "<null or a short note on any part you could not read>",
        "marks_awarded": <integer>,
        "marks_total": <integer>,
        "breakdown": [
            {{"point": "<mark scheme point in your own words>", "status": "met | partially_met | missed", "reasoning": "<brief reasoning>"}}
        ],
        "overall_feedback": "<1-3 sentences of constructive feedback for the student>"
    }}
"""

    userContent: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": f"Grade the attached handwritten answer for the question {questionNumber} against the attached mark scheme."
        },
        {
            "type": "file",
            "file": {
                "filename": "mark_scheme.pdf",
                "file_data": markSchemeEncoded
            },
        },
    ]

    for encodedImg in answerImagesEncodedArr:
        userContent.append({
            "type": "image_url",
            "image_url": {
                "url": encodedImg
            }
        })

    lastError = "Unknown Error"
    response = None

    for attempt in range(3):
        try:
            response = requests.post(
                "https://ai.hackclub.com/proxy/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {aiKey}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": aiModel,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": userContent
                        }
                    ]
                },
                timeout=60
            )

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            lastError = f"Hack Club AI API Request Failed: {e}"
            response = None

            if attempt < 2:
                time.sleep(2 ** attempt)
    if response is None:
        return False, lastError

    try:
        responseData = response.json()
        content = responseData["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        return False, f"Unexpected API Response Structure: {e}"

    cleanContent = content.strip()

    if cleanContent.startswith("```"):
        cleanContent = cleanContent.strip("`")
        if cleanContent.lower().startswith("json"):
            cleanContent = cleanContent[4:]

        cleanContent = cleanContent.strip()

    try:
         resultJson = json.loads(cleanContent)
    except json.JSONDecodeError as e:
        return False, f"Model did not return valid JSON Response: {e}. Raw Response: {content}"

    return True, resultJson

def gradeTypedAnswer(subjectName, subjectCode, examinationYear, examinationSeries, variant, questionNumber, markSchemePath, answerText):
    if not aiKey:
        return False, "Hack Club AI API Key Missing :("

    if not answerText or not answerText.strip():
        return False, "No answer text provided :("

    markSchemeDownloadStatus, markSchemeBytes = downloadFromSupabase("papers", markSchemePath)

    if not markSchemeDownloadStatus:
        return False, f"Failed to download mark scheme from storage: {markSchemeBytes}"

    assert isinstance(markSchemeBytes, bytes)

    markSchemeEncoded = encodeBytesToBase64Uri(markSchemeBytes, "application/pdf")

    SYSTEM_PROMPT = f"""
You are an experienced {subjectName} examiner grading a student's typed answer for CAIE O Level Exam ({subjectName}, code {subjectCode}, {examinationYear} {examinationSeries}, variant {variant}).
    You will be given:
    1. The official mark scheme PDF for that full paper.
    2. The student's typed answer to Question {questionNumber}, exactly as they typed it.

    Your Task:
    1. Locate question {questionNumber} in the mark scheme and identify each individual mark scheme point (each thing that earns credit) and maximum marks available.
    2. Compare the typed answer against each mark scheme point and decide whether it was met, partially met or missed with brief reasoning for each.
    3. Sum the marks awarded.

    Also identify the specific {subjectName} topic this question tests, using a consistent, standard O-Level topic name.

    Respond with ONLY a single valid JSON object, no markdown code fence, no preamble, no explanation outside the JSON. Use exactly this structure:
    {{
        "question_number_requested": "{questionNumber}",
        "topic": "<standard topic name for this question>",
        "marks_awarded": <integer>,
        "marks_total": <integer>,
        "breakdown": [
            {{"point": "<mark scheme point in your own words>", "status": "met | partially_met | missed", "reasoning": "<brief reasoning>"}}
        ],
        "overall_feedback": "<1-3 sentences of constructive feedback for the student>"
    }}
"""

    userContent: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": f"Grade this typed answer for question {questionNumber} against the attached mark scheme.\n\nStudent's Answer:\n{answerText}"
        },
        {
            "type": "file",
            "file": {
                "filename": "mark_scheme.pdf",
                "file_data": markSchemeEncoded
            },
        },
    ]

    lastError = "Unknown Error"
    response = None

    for attempt in range(3):
        try:
            response = requests.post(
                "https://ai.hackclub.com/proxy/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {aiKey}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": aiModel,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": userContent
                        }
                    ]
                },
                timeout=60
            )

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            lastError = f"Hack Club AI API Request Failed: {e}"
            response = None
            if attempt < 2:
                time.sleep(2 ** attempt)

    if response is None:
        return False, lastError

    try:
        responseData = response.json()
        content = responseData["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        return False, f"Unexpected API Response Structure: {e}"

    cleanContent = content.strip()

    if cleanContent.startswith("```"):
        cleanContent = cleanContent.strip("`")

        if cleanContent.lower().startswith("json"):
            cleanContent = cleanContent[4:]

        cleanContent = cleanContent.strip()

    try:
        resultJson = json.loads(cleanContent)
    except json.JSONDecodeError as e:
        return False, f"Model didn't return valid JSON: {e}. Raw Response: {content}"

    resultJson["transcription"] = answerText
    resultJson.setdefault("question_number_detected_in_image", None)
    resultJson.setdefault("question_number_mismatch_warning", None)
    resultJson.setdefault("illegible_sections", None)

    return True, resultJson

def segmentAnswerScript(answerImagesPath):
    if not aiKey:
        return False, "Hack Club AI API Key Missing :("
    if not answerImagesPath:
        return False, "No Answer Images Provided :("

    answerImagesEncodedArr = []

    for imagePath in answerImagesPath:
        imageDownloadStatus, imageBytes = downloadFromSupabase("answer-uploads", imagePath)

        if not imageDownloadStatus:
            return False, f"Failed to download answeimage '{imagePath}' from storage: {imageBytes}"

        assert isinstance(imageBytes, bytes)

        compressedImageBytes = compressImageBytes(imageBytes)

        answerImageEncoded = encodeBytesToBase64Uri(compressedImageBytes, "image/jpeg")
        answerImagesEncodedArr.append(answerImageEncoded)

    SYSTEM_PROMPT = """
You are looking at a set of images, in no guaranteed order, representing pages of a student's handwritten exam answer script. The upload order does not necessarily match the actual page order of the document.

    Your Task:
    1. Identify question numbers written by the student or printed on the page (e.g. "Q4", "4(a)", a bold question number at the start of a section) across the images.
    2. Use any printed page numbers visible on each page (commonly at the top or bottom) to determine the true document order, rather than assuming upload order is correct.
    3. Each image in this request is immediately preceded by a text label stating its exact index (e.g. "Image index 0:"). Use these stated labels directly — do not count image position yourself, use the number given in the label.
    4. A question's answer may span multiple images. A single image may contain the end of one question and the start of another; in that case, include that image index in both segments.
    5. Some images may not be part of any question's answer at all (e.g. a cover page, instructions page, or blank page). Do not force these into a segment.

    Respond with ONLY a single valid JSON object, no markdown code fence, no preamble, no explanation outside the JSON. Use exactly this structure:
    {
        "segments": [
            {
                "question_number": "<question number as written by student>",
                "image_indices": [<zero-based index integers, in true reading order for this question>]
            }
        ],
        "unmatched_image_indices": [<zero-based indices of any images that don't clearly belong to a question>]
    }
"""

    userContent: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": "Identify the question segments across the attached answer script."
        },
    ]

    for index, encodedImg in enumerate(answerImagesEncodedArr):
        userContent.append({
            "type": "text",
            "text": f"Image index {index}:"
        })
        userContent.append({
            "type": "image_url",
            "image_url": {
                "url": encodedImg
            }
        })

    lastError = "Unknown Error"
    response = None

    for attempt in range(3):
        try:
            response = requests.post(
                "https://ai.hackclub.com/proxy/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {aiKey}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": aiModel,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": userContent
                        }
                    ]
                },
                timeout=90
            )

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            lastError = f"Hack Club AI API Request Failed: {e}"
            response = None
            if attempt < 2:
                time.sleep(2 ** attempt)
    if response is None:
        return False, lastError

    try:
        responseData = response.json()
        content = responseData["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        return False, f"Unexpected API Response Structure: {e}"

    cleanContent = content.strip()

    if cleanContent.startswith("```"):
        cleanContent = cleanContent.strip("`")
        if cleanContent.lower().startswith("json"):
            cleanContent = cleanContent[4:]

        cleanContent = cleanContent.strip()

    try:
        resultJson = json.loads(cleanContent)
    except json.JSONDecodeError as e:
        return False, f"Model didn't returned valid JSON Response: {e}. Raw Response: {content}"

    return True, resultJson

def signUpUser(email, password):
    try:
        authClient = create_client(supabaseUrl, supabaseKey, options=SyncClientOptions(storage_client_timeout=60))

        response = authClient.auth.sign_up({
            "email": email,
            "password": password
        })

        if response.user is None or response.session is None:
            return False, "Sign Up Failed. Please Try Again!"

        return True, {
            "userId": response.user.id,
            "accessToken": response.session.access_token
        }
    except Exception as e:
        return False, str(e)

def signInUser(email, password):
    try:
        authClient = create_client(supabaseUrl, supabaseKey, options=SyncClientOptions(storage_client_timeout=60))
        response = authClient.auth.sign_in_with_password(
            {
                "email": email,
                "password": password
            }
        )

        if response.user is None or response.session is None:
            return False, "Invalid Email or Password."

        return True, {
            "userId": response.user.id,
            "accessToken": response.session.access_token
        }

    except Exception as e:
        return False, str(e)

def insertGradingHistory(userId, subjectName, subjectCode, examinationYear, examinationSeries, variant, questionNumber, resultJson):
    try:
        response = supabase.table("grading_history").insert({
            "user_id": userId,
            "subject_name": subjectName,
            "subject_code": str(subjectCode),
            "examination_year": str(examinationYear),
            "examination_series": examinationSeries,
            "variant": str(variant),
            "question_number": str(questionNumber),
            "topic": resultJson.get("topic"),
            "marks_awarded": resultJson.get("marks_awarded"),
            "marks_total": resultJson.get("marks_total"),
            "result_json": resultJson
        }).execute()

        if not response.data:
            return False, f"Insert returned no data. Full response: {response}"

        return True, response.data[0]["id"]
    except Exception as e:
        return False, str(e)

def getGradingHistory(userId, limit=50):
    try:
        response = supabase.table("grading_history").select("*").eq("user_id", userId).order("created_at", desc=True).limit(limit).execute()
        return True, response.data
    except Exception as e:
        return False, str(e)

def getGradingHistoryEntry(userId, entryId):
    try:
        response = supabase.table("grading_history").select("*").eq("user_id", userId).eq("id", entryId).limit(1).execute()

        if not response.data:
            return False, "Entry not found :("

        return True, response.data[0]
    except Exception as e:
        return False, str(e)

def getWeakTopics(userId):
    historyStatus, historyData = getGradingHistory(userId, limit=200)

    if not historyStatus:
        return False, historyData

    assert isinstance(historyData, list)

    topicStats = {}

    for entry in historyData:
        topic = entry.get("topic")
        marksAwarded = entry.get("marks_awarded")
        marksTotal = entry.get("marks_total")

        if not topic or marksAwarded is None or marksTotal is None or marksTotal == 0:
            continue

        if topic not in topicStats:
            topicStats[topic] = {
                "marksAwarded": 0,
                "marksTotal": 0,
                "questionCount": 0
            }

        topicStats[topic]["marksAwarded"] += marksAwarded
        topicStats[topic]["marksTotal"] += marksTotal
        topicStats[topic]["questionCount"] += 1

    topicList = []

    for topic, stats in topicStats.items():
        percentage = round((stats["marksAwarded"] / stats["marksTotal"]) * 100, 1)

        topicList.append({
            "topic": topic,
            "percentage": percentage,
            "marksAwarded": stats["marksAwarded"],
            "marksTotal": stats["marksTotal"],
            "questionCount": stats["questionCount"]
        })

    topicList.sort(key=lambda t: t["percentage"])

    return True, topicList

def genFlashCardsFromResult(userId, subjectName, topic, sourceEntryId, resultJson):
    breakdown = resultJson.get("breakdown", [])
    createdCount = 0

    for point in breakdown:
        status = point.get("status")

        if status not in ("missed", "partially_met"):
            continue

        front = f"{subjectName}: {point.get('point')}"
        back = point.get("reasoning", "No explaination available.")

        try:
            supabase.table("flashcards").insert({
                "user_id": userId,
                "source_entry_id": sourceEntryId,
                "subject_name": subjectName,
                "topic": topic,
                "front": front,
                "back": back
            }).execute()

            createdCount += 1
        except Exception as e:
            print(f"Failed to create flashcard: {e}")

    return createdCount

def getDueFlashCards(userId, limit=20):
    try:
        todayDate = date.today().isoformat()
        response = supabase.table("flashcards").select("*").eq("user_id", userId).lte("next_review_date", todayDate).order("next_review_date").limit(limit).execute()

        return True, response.data
    except Exception as e:
        return False, str(e)

def reviewFlashcard(userId, flashCardId, quality):
    try:
        cardResp = supabase.table("flashcards").select("*").eq("user_id", userId).eq("id", flashCardId).limit(1).execute()

        if not cardResp.data:
            return False, "Flash Card not found :("

        card = cardResp.data[0]

        easeFactor = card["ease_factor"]
        intervalDays = card["interval_days"]

        if quality < 3:
            intervalDays = 1
        else:
            if intervalDays <= 1:
                intervalDays = 6
            else:
                intervalDays = round(intervalDays * easeFactor)

            easeFactor = max(1.3, easeFactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        nextReviewDate = (date.today() + timedelta(days=intervalDays)).isoformat()

        updateResp = supabase.table("flashcards").update(
            {
                "interval_days": intervalDays,
                "ease_factor": easeFactor,
                "next_review_date": nextReviewDate
            }
        ).eq("id", flashCardId).execute()

        if not updateResp.data:
            return False, "Failed to update flashcard."

        return True, None
    except Exception as e:
        return False, str(e)

def insertChatMessage(userId, role, content):
    try:
        response = supabase.table("coach_chat_history").insert({
            "user_id": userId,
            "role": role,
            "content": content
        }).execute()

        if not response.data:
            return False, f"Insert returned no data. Raw Response: {response}"

        return True, None
    except Exception as e:
        return False, str(e)

def getChatHistory(userId, limit=50):
    try:
        response = supabase.table("coach_chat_history").select("*").eq("user_id", userId).order("created_at", desc=False).limit(limit).execute()
        return True, response.data
    except Exception as e:
        return False, str(e)

def coachChat(userId, userMsg, aboutEntryId=None):
    if not aiKey:
        return False, "Hack Club AI API Key Missing :("

    gradingHistoryStatus, gradingHistoryData = getGradingHistory(userId, limit=15)

    if not gradingHistoryStatus:
        gradingHistoryData = []

    specificEntryContext = ""

    if aboutEntryId:
        entryStatus, entryData = getGradingHistoryEntry(userId, aboutEntryId)

        if entryStatus:
            assert isinstance(entryData, dict)
            resultJson = entryData.get("result_json", {})
            breakdownLines = []

            for point in resultJson.get("breakdown", []):
                breakdownLines.append(f"- {point.get('point')}: {point.get('status')} ({point.get('reasoning')})")

            specificEntryContext = f"""
The student specifically wants to discuss this question right now:
Subject: {entryData.get('subject_name')}, Question {entryData.get('question_number')}, Score: {entryData.get('marks_awarded')}/{entryData.get('marks_total')}
Transcription of their answer: {resultJson.get('transcription', 'N/A')}
Mark Scheme Breakdown:
{chr(10).join(breakdownLines)}
Overall Feedback Given: {resultJson.get('overall_feedback', 'N/A')}

Focus your response on this specific question unless student diverts the conversation elsewhere.
"""

    chatHistoryStatus, chatHistoryData = getChatHistory(userId, limit=50)

    if not chatHistoryStatus:
        chatHistoryData = []

    if gradingHistoryData:
        summaryLines = []

        for entry in gradingHistoryData:
            assert isinstance(entry, dict)
            summaryLines.append(
                f"- {entry.get('subject_name')} {entry.get('examination_year')} {entry.get('examination_series')} "
                f"Q{entry.get('question_number')}: {entry.get('marks_awarded')}/{entry.get('marks_total')}"
            )
        gradingSummary = "\n".join(summaryLines)
    else:
        gradingSummary = "No past graded questions available yet."

    SYSTEM_PROMPT = f"""
You are a highly professional, expert O Level tutor and examiner, acting as a personal study coach for this student. Here's the student's recent grading history (most recent first). Reference specifically subjects, question numbers and scores from this list by name whenever it's relevant to the conversation rather than speaking in vague generalities: {gradingSummary}. Be encouraging but honest, direct, short, concise. Use correct O Level curriculum terminology and give concrete actionable study advice. If the student's history shows a pattern of losing marks on particular topic, point it out directly and specifically.
Write in plain, unformatted prose only - don't use markdown syntax of anykind - no asterisks for bold or italics, no headers, no bullet-point markers like "-" or "*", no numbered list formatting. If you want to list multiple points, write them as separate plain sentences or separate paragraphs instead.{specificEntryContext}
"""

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    assert isinstance(chatHistoryData, list)

    for pastMsg in chatHistoryData:
        messages.append(
            {
                "role": pastMsg["role"],
                "content": pastMsg["content"]
            }
        )

    messages.append(
        {
            "role": "user",
            "content": userMsg
        }
    )

    lastError = "Unknown Error"
    response = None

    for attempt in range(3):
        try:
            response = requests.post(
                "https://ai.hackclub.com/proxy/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {aiKey}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": aiModel,
                    "messages": messages
                },
                timeout=60
            )

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            lastError = f"Hack Club AI API Request Failed: {e}"
            response = None

            if attempt < 2:
                time.sleep(2 ** attempt)

    if response is None:
        return False, lastError

    try:
        responseData = response.json()
        reply = responseData["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        return False, f"Unexpected API Response Strucutre: {e}"

    insertStatus, insertError = insertChatMessage(userId, "user", userMsg)

    if not insertStatus:
        print(f"Failed to save user chat message: {insertError}")

    insertStatus, insertError = insertChatMessage(userId, "assistant", reply)

    if not insertStatus:
        print(f"Failed to save assistant chat message: {insertError}")

    return True, reply

SUBJECT_SYLLABUS_URLS = {
    "5054": "https://www.cambridgeinternational.org/Images/697324-2026-2028-syllabus.pdf",
    "5090": "https://www.cambridgeinternational.org/Images/697330-2026-2028-syllabus.pdf",
    "5070": "https://www.cambridgeinternational.org/Images/697326-2026-2028-syllabus.pdf",
    "4024": "https://www.cambridgeinternational.org/Images/662480-2025-2027-syllabus.pdf",
    "1123": "https://www.cambridgeinternational.org/Images/634453-2024-2026-syllabus.pdf"
}

def getSyllabusPdf(subjectCode):
    subjectCode = str(subjectCode)
    storagePath = f"syllabus/{subjectCode}.pdf"

    availability = checkExistInSupabase("papers", storagePath)

    if availability:
        return True, storagePath

    syllabusUrl = SUBJECT_SYLLABUS_URLS.get(subjectCode)

    if not syllabusUrl:
        return False, "No known syllabus URL for this subject code."

    lastError = "Unknown Error"
    response = None

    for attempt in range(3):
        try:
            response = requests.get(syllabusUrl, headers=headers, timeout=30)
            response.raise_for_status()
            break
        except Exception as e:
            lastError = str(e)
            response = None
            if attempt < 2:
                time.sleep(2 ** attempt)

    if response is None:
        return False, lastError

    uploadStatus, uploadResult = uploadToSupabase("papers", storagePath, response.content, "application/pdf")

    if not uploadStatus:
        return False, uploadResult

    return True, storagePath

def genProgressRepPdf(userId, userEmail):
    historyStatus, historyData = getGradingHistory(userId, limit=200)

    if not historyStatus:
        return False, historyData

    topicStatus, topicData = getWeakTopics(userId)

    if not topicStatus:
        topicData = []

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("OLeveliPy Progress Report", styles["Title"]))
    content.append(Paragraph(f"Student: {userEmail}", styles["Normal"]))
    content.append(Paragraph(f"Generated: {date.today().isoformat()}", styles["Normal"]))
    content.append(Spacer(1, 20))

    totalMarksAwarded = 0
    totalMarksPossible = 0

    for entry in historyData:
        awarded = entry.get("marks_awarded")
        if awarded is None:
            awarded = 0

        possible = entry.get("marks_total")
        if possible is None:
            possible = 0

        totalMarksAwarded += awarded
        totalMarksPossible += possible

    if totalMarksPossible > 0:
        overallPercentage = round((totalMarksAwarded / totalMarksPossible) * 100, 1)
    else:
        overallPercentage = 0

    content.append(Paragraph("Summary", styles["Heading1"]))
    content.append(Paragraph(f"Total Questions Graded: {len(historyData)}", styles["Normal"]))
    content.append(Paragraph(f"Overall Score: {overallPercentage}% ({totalMarksAwarded}/{totalMarksPossible})", styles["Normal"]))
    content.append(Spacer(1, 20))

    content.append(Paragraph("Topic Breakdown (Weakest -> Strongest)", styles["Heading1"]))

    if topicData:
        tableRows = [
            [
                "Topic",
                "Score",
                "Questions"
            ]
        ]

        for topic in topicData:
            tableRows.append([
                topic["topic"],
                f"{topic['percentage']}% ({topic['marksAwarded']}/{topic['marksTotal']})",
                str(topic["questionCount"])
            ])

        topicTable = Table(tableRows, colWidths=[260, 150, 80])
        topicTable.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))

        content.append(topicTable)
    else:
        content.append(Paragraph("No topic data available yet.", styles["Normal"]))

    content.append(Spacer(1, 20))
    content.append(Paragraph("Recent Grading History", styles["Heading1"]))

    if historyData:
        historyRows = [
            [
                "Date",
                "Subject",
                "Exam",
                "Question",
                "Score"
            ]
        ]

        for entry in historyData[:50]:
            historyRows.append(
                [
                    str(entry.get("created_at", ""))[:10],
                    str(entry.get("subject_name", "")),
                    f"{entry.get('examination_year', '')} {entry.get('examination_series', '')}",
                    str(entry.get('question_number', "")),
                    f"{entry.get('marks_awarded')}/{entry.get('marks_total')}"
                ]
            )

        historyTable = Table(historyRows, colWidths=[70, 90, 100, 80, 60])
        historyTable.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("GRID", (0,0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0,0), (-1,-1), 8),
        ]))

        content.append(historyTable)
    else:
        content.append(Paragraph("No grading history yet.", styles["Normal"]))

    pdfBuffer = io.BytesIO()
    doc = SimpleDocTemplate(pdfBuffer, pagesize=letter)
    doc.build(content)

    return True, pdfBuffer.getvalue()

def genPracticeMsPdf(subjectName, topic, questionTxt, markSchemePoints, marksTotal):
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"{subjectName} Practice Question - {topic}", styles["Title"]))
    content.append(Spacer(1, 12))
    content.append(Paragraph("Question 1", styles["Heading1"]))
    content.append(Paragraph(questionTxt, styles["Normal"]))
    content.append(Spacer(1, 20))

    content.append(Paragraph("Mark Scheme", styles["Heading1"]))

    rows = [
        [
            "Point",
            "Marks"
        ]
    ]

    for point in markSchemePoints:
        rows.append([point.get("point", ""), str(point.get("marks", ""))])

    table = Table(rows, colWidths=[400, 60])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0,0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    content.append(table)
    content.append(Spacer(1, 12))
    content.append(Paragraph(f"Total Marks: {marksTotal}", styles["Normal"]))

    pdfBuffer = io.BytesIO()
    doc = SimpleDocTemplate(pdfBuffer, pagesize=letter)
    doc.build(content)

    return pdfBuffer.getvalue()

def genPracticeQuestions(userId, subjectName, subjectCode, topic):
    if not aiKey:
        return False, "Hack Club AI API Key Missing :("

    syllabusStatus, syllabusResult = getSyllabusPdf(subjectCode)

    syllabusFileBlock = None

    if syllabusStatus:
        syllabusDownloadStatus, syllabusBytes = downloadFromSupabase("papers", syllabusResult)

        if syllabusDownloadStatus:
            syllabusFileBlock = {
                "type": "file",
                "file": {
                    "filename": "syllabus.pdf",
                    "file_data": encodeBytesToBase64Uri(syllabusBytes, "application/pdf")
                }
            }

    if syllabusFileBlock:
        instruction = """The official CAIE Syllabus Document for this subject is attached. You MUST base the scope, depth and wording of the question strictly on what's actually listed in the attached syllabus for this topic - do not test content beyond what the syllabus specifies for this topic and use the syllabus's own command words where applicable."""
    else:
        instruction = f"""No official syllabus document is available for this subject in this system. Use your best knowledge of standard, current O Level CAIE {subjectName} syllabus for this topic and be conservative - stay within commonly taught, standard scopre for this topic rather than including advanced, unusual or ambiguous content that might not be part of every version of the syllabus"""

    SYSTEM_PROMPT = f"""
You are an expereinced {subjectName} examiner writing an original O Level Standard Practice Question on the topic "{topic}".

{instruction}

Write one question, at a difficulty and style consistent with real CAIE O Level {subjectName} papers, along with a proper mark scheme breaking down exactly how marks are awarded.

Respond with ONLY with a single valid JSON Object, no markdown code fence, no preamble, no explaination out JSON. Use exactly this structure:
{{
    "question_text": "<the full question text, including any necessary data/values needed to answer it>",
    "marks_total": <integer, sum of all individual point marks>,
    "mark_scheme_points": [
        {{"point": "<what earns credit, in mark-scheme style wording>", "marks": <integer marks for this point>}}
    ]
}}
"""

    userContent: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": f"Generate one practice question on {topic}."
        }
    ]

    lastError = "Unknown Error"
    response = None

    for attempt in range(3):
        try:
            response = requests.post(
                "https://ai.hackclub.com/proxy/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {aiKey}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": aiModel,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": userContent
                        }
                    ]
                },
                timeout=60
            )

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            lastError = f"Hack Club AI API Request Failed: {e}"
            response = None

            if attempt < 2:
                time.sleep(2 ** attempt)

    if response is None:
        return False, lastError

    try:
        responseData = response.json()
        content = responseData["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        return False, f"Unexpected API Response Structure: {e}"

    cleanContent = content.strip()

    if cleanContent.startswith("```"):
        cleanContent = cleanContent.strip("`")

        if cleanContent.lower().startswith("json"):
            cleanContent = cleanContent[4:]

        cleanContent = cleanContent.strip()

    try:
        questionData = json.loads(cleanContent)
    except json.JSONDecodeError as e:
        return False, f"Model did not return valid JSON: {e}. Raw Response: {content}"

    questionText = questionData.get("question_text")
    marksTotal = questionData.get("marks_total")
    markSchemePoints = questionData.get("mark_scheme_points", [])

    if not questionText or not marksTotal or not markSchemePoints:
        return False, "Missing Data in AI Response."

    pdfBytes = genPracticeMsPdf(subjectName, topic, questionText, markSchemePoints, marksTotal)

    storagePath = f"generated/{str(uuid.uuid4())}_ms.pdf"

    uploadStatus, uploadResult = uploadToSupabase("papers", storagePath, pdfBytes, "application/pdf")

    if not uploadStatus:
        return False, f"Failed to upload generated mark scheme: {uploadResult}"

    try:
        insertResponse = supabase.table("practice_questions").insert({
            "user_id": userId,
            "subject_name": subjectName,
            "topic": topic,
            "question_text": questionText,
            "marks_total": marksTotal,
            "mark_scheme_path": storagePath
        }).execute()

        if not insertResponse.data:
            return False, f"Insert returned no data. Full response: {insertResponse}"

        return True, insertResponse.data[0]
    except Exception as e:
        return False, str(e)

def getPracticeQuestions(userId, limit=50):
    try:
        response = supabase.table("practice_questions").select("*").eq("user_id", userId).order("created_at", desc=True).limit(limit).execute()

        return True, response.data
    except Exception as e:
        return False, str(e)

def getPracticeQuestionEntry(userId, questionId):
    try:
        response = supabase.table("practice_questions").select("*").eq("user_id", userId).eq("id", questionId).limit(1).execute()

        if not response.data:
            return False, "Practice Question not found."

        return True, response.data[0]
    except Exception as e:
        return False, str(e)

def getDashboardData(userId):
    dueStatus, dueCards = getDueFlashCards(userId, limit=100)

    if dueStatus:
        dueCount = len(dueCards)
    else:
        dueCount = 0

    topicStatus, topicData = getWeakTopics(userId)

    if topicStatus and topicData:
        weakestTopic = topicData[0]
    else:
        weakestTopic = None

    historyStatus, historyData = getGradingHistory(userId, limit=5)

    if historyStatus:
        recentHistory = historyData
    else:
        recentHistory = []

    fullHistoryStatus, fullHistoryData = getGradingHistory(userId, limit=200)

    if fullHistoryStatus:
        totalGraded = len(fullHistoryData)
        totalAwarded = 0
        totalPossible = 0

        for entry in fullHistoryData:
            totalAwarded += entry.get("marks_awarded") or 0
            totalPossible += entry.get("marks_total") or 0

        if totalPossible > 0:
            overallPct = round((totalAwarded / totalPossible) * 100, 1)

    return {
        "dueFlashcardCount": dueCount,
        "weakestTopic": weakestTopic,
        "recentHistory": recentHistory,
        "totalGraded": totalGraded,
        "overallPercentage": overallPct
    }