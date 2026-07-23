import requests, os, base64, json
from typing import Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

aiModel = "google/gemini-3.1-flash-lite"

supabaseUrl = os.getenv("SUPABASE_URL")
supabaseKey = os.getenv("SERVICE_ROLE_KEY")
aiKey = os.getenv("HCAI_KEY")

if not supabaseUrl or not supabaseKey:
    raise RuntimeError("SUPABASE_URL and SERVICE_ROLE_KEY must be set in your environment variables file (.env)")

supabase: Client = create_client(supabaseUrl, supabaseKey)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def uploadToSupabase(bucketName, destinationPath, fileBytes, contentType):
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
        return False, str(e)

def downloadFromSupabase(bucketName, filePath):
    try:
        fileBytes = supabase.storage.from_(bucketName).download(filePath)
        return True, fileBytes
    except Exception as e:
        return False, str(e)

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

    try:
        response = requests.get(downloadUrl, headers=headers)
        response.raise_for_status()
    except Exception as e:
        return False, str(e)

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

        answerImageEncoded = encodeBytesToBase64Uri(imageBytes, "image/jpeg")

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

    Respond with ONLY a single valid JSON object, no mark down code fence, no preamble, no explaination outside the JSON. Use exactly this structure:
    {{
        "question_number_requested": "{questionNumber}",
        "question_number_detected_in_image": "<question number you acutally see written, or null if unclear>",
        "question_number_mismatch_warning": "<null or a short note if detected number differs from requested>",
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
    except requests.exceptions.RequestException as e:
        return False, f"Hack Club AI API Request Failed: {e}"

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

        answerImageEncoded = encodeBytesToBase64Uri(imageBytes, "image/jpeg")
        answerImagesEncodedArr.append(answerImageEncoded)

    SYSTEM_PROMPT = """
You are looking at a sequence of images, in order, representing pages of a student's handwritten exam answer script.

    Your Task:
    1. Identify question numbers written by the student (e.g. "Q4", "4(a)") across the pages.
    2. Group the images into segments, one per question, using zero-based image index (0 = first image provided, 1 = second, and so on).
    3. A question's answer may span multiple consecutive images. A single image may contain the end of one question and the start of another; in that case, include that image index in both segments.

    Respond with ONLY a single valid JSON object, no markdown code fence, no preamble, no explanation outside the JSON. Use exactly this structure:
    {
        "segments": [
            {
                "question_number": "<question number as written by student>",
                "image_indices": [<zero-based index integers>]
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

    for encodedImg in answerImagesEncodedArr:
        userContent.append({
            "type": "image_url",
            "image_url": {
                "url": encodedImg
            }
        })

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
            timeout=30
        )

        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return False, f"Hack Club AI API Request Failed: {e}"

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