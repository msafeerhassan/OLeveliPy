import requests, os, base64, json
from pathlib import Path

aiModel = "google/gemini-3.1-flash-lite"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


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

    downloadURL = f"{baseUrl}/download"

    currentDir = os.path.dirname(os.path.abspath(__file__))

    folderName = "files"

    mainFolderOutputPath = Path(os.path.join(currentDir, folderName))

    msFolderOutputPath = Path(os.path.join(currentDir, folderName, "ms"))

    qpFolderOutputPath = Path(os.path.join(currentDir, folderName, "qp"))

    if mainFolderOutputPath.is_dir():
        pass
    else:
        os.mkdir(folderName)
    
    if msFolderOutputPath.is_dir():
        pass
    else:
        os.mkdir("files/ms")

    if qpFolderOutputPath.is_dir():
        pass
    else:
        os.mkdir("files/qp")

    outputPath = os.path.join(currentDir, folderName, fileTypeFormatted, fileName)

    # print(outputPath)

    try:
        response = requests.get(downloadURL, headers=headers, stream=True)

        response.raise_for_status()

        with open(outputPath, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        return True, outputPath
    except Exception as e:
        return False, e

def getAllPresentFiles(targetType):
    dirPath = f"files/{targetType}"

    if targetType == "ms":
        fileType = "Mark Scheme"
    elif targetType == "qp":
        fileType = "Question Paper"
    else:
        fileType = "Error"

    fileNames = []

    for file in os.listdir(dirPath):
        formattedData = file.split("_")
        subjectName = formattedData[0].capitalize()
        subjectCode = int(formattedData[1])
        examinationYear = int(formattedData[2])
        examinationSeries = formattedData[3]
        formattedExamSeriesArr = examinationSeries.split("-")
        formattedExamSeriesStr = formattedExamSeriesArr[0].capitalize() + " " + formattedExamSeriesArr[1].capitalize()
        examVariant = int(formattedData[5])

        # print(f"\nSubject: {subjectName}\nSubject Code: {subjectCode}\nExamination Year: {examinationYear}\nExamination Series: {formattedExamSeriesStr}\nExam Variant: {examVariant}\nFile Type: {fileType}\n")

def checkFilePresent(subjectName: str, subjectCode, examinationYear, examinationSeries:str, shortenedCode:str, variant, fileType):
    dirPath = f"files/{fileType.lower()}"

    subjectNameFormatted = subjectName.lower()

    subjectCodeFormatted = int(subjectCode)

    examinationYearFormatted = int(examinationYear)

    examinationSeriesFormatted = examinationSeries.lower()

    shortenedCodeFormatted = shortenedCode.lower()

    fileTypeFormatted = fileType.lower()

    variantFormatted = int(variant)

    targetFileName = f"{subjectNameFormatted}_{subjectCodeFormatted}_{examinationYearFormatted}_{examinationSeriesFormatted}_{shortenedCodeFormatted}_{variantFormatted}_{fileTypeFormatted}.pdf"

    for file in os.listdir(dirPath):
        if file == targetFileName:
            return True, os.path.join(dirPath, file)
        else:
            continue

    return False, None

def encodeFileToBase64Uri(filePath: str, mimeType: str):
    with open(filePath, "rb") as file:
        encodedData = base64.b64encode(file.read()).decode("utf-8")
    
    return f"data:{mimeType};base64,{encodedData}"

def pastPaperChecker(subjectName, subjectCode, examinationYear, examinationSeries, variant, questionNumber, markSchemePath, answerImagesPath):
    apiKey = os.getenv("HCAI_KEY")

    if not apiKey:
        return False, "Hack Club AI API Key Missing :("
    
    if not answerImagesPath:
        return False, "No answer images provided :("
    
    try:
        markSchemeEncoded = encodeFileToBase64Uri(markSchemePath, "application/pdf")
    except Exception as e:
        return False, f"Failed to read mark scheme file: {e}"
    
    answerImagesEncodedArr = []

    for imagePath in answerImagesPath:
        try:
            answerImageEncoded = encodeFileToBase64Uri(imagePath, "image/jpeg")
            answerImagesEncodedArr.append(answerImageEncoded)
        except Exception as e:
            return False, f"Failed to read answer image '{imagePath}': {e}"
    
    SYSTEM_PROMPT = f"""You are an experienced {subjectName} examiner grading a student's handwritten answer for CAIE O Level Exam ({subjectName}, code {subjectCode}, {examinationYear} {examinationSeries}, variant {variant}).
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
            {
                {
                    "point": "<mark scheme point in your own words>",
                    "status": "met | partially_met | missed",
                    "reasoning": "<brief reasoning>"
                }
            }
        ],
        "overall_feedback": "<1-3 sentences of constructive feedback for the student>"
    }}
    """

    userContent = [
        {
            "type": "text",
            "text": f"Grade the attached handwritten answer for question {questionNumber} against the attached mark scheme."
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
                "Authorization": f"Bearer {apiKey}",
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
        reponseData = response.json()
        content = reponseData["choices"][0]["message"]["content"]
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
        return False, f"Model did not return valid JSON: {e}. Raw Response: {content}"
    
    return True, resultJson

def checkAllPastPaper(subjectName, subjectCode, examinationYear, examinationSeries, variant, markSchemePath, answerImagesPath):
    apiKey = os.getenv("HCAI_KEY")

    if not apiKey:
        return False, "Hack Club AI API Key Missing :("
    
    if not answerImagesPath:
        return False, "No answer images provided :("
    
    try:
        markSchemeEncoded = encodeFileToBase64Uri(markSchemePath, "application/pdf")
    except Exception as e:
        return False, f"Failed to read mark scheme file: {e}"
    
    answerImagesEncodedAarr = []

    for imagePath in answerImagesPath:
        try:
            answerImageEncoded = encodeFileToBase64Uri(imagePath, "image/jpeg")
            answerImagesEncodedAarr.append(answerImageEncoded)
        except Exception as e:
            return False, f"Failed to read answer image '{imagePath}': {e}"
    
    SYSTEM_PROMPT = f"""You are an experienced {subjectName} examiner grading a full set of student's handwritten answer for CAIE O Level Exam ({subjectName}, code {subjectCode}, {examinationYear} {examinationSeries}, variant {variant}).
    You will be given:
    1. The official mark scheme PDF For that full paper.
    2. A sequence of images, in order, representing all the pages of a student's handwritten answer script. A signle question's answer may span multiple pages and a single page may contain end of one question and start of other.

    Your Task:
    1. Go through the pages in order and identify question boundaries based on question numbers written by the student (e.g. "Q4", "4(a)").
    2. For each question you find, transcribe the student's answer, locate that question in the mark scheme and grade it: compare against each mark scheme point and award marks.
    3. If a page or seciton doesn't clearly belong to any question, note it rather than silently dropping or randomly marking it.
    4. If the same question number appears more than once (e.g. crossed out and redone), grade the final attempt and note duplicate.


    Also, read other general instructions mentioned regarding checking paper in the mark scheme.

    Respond with ONLY a single valid JSON object, no mark down code fence, no preamble, no explaination outside the JSON. Use exactly this structure:
    {{
        "questions": [
            {{
                "question_number_detected": "<question number you acutally see written>",
                "transcription": "<full transcription of the handwritten answer for this question>",
                "illegible_sections": "<null or a short note on any part you could not read>",
                "marks_awarded": <integer>,
                "marks_total": <integer>,
                "breakdown": [
                    {
                        {
                            "point": "<mark scheme point in your own words>",
                            "status": "met | partially_met | missed",
                            "reasoning": "<brief reasoning>"
                        }
                    }
                ],
                "overall_feedback": "<1-3 sentences of constructive feedback for the student>"
                }}
        ],
        "unmatched_sections": "<null or a short note on any pages/content you could not attribute to a specific question>"
    }}
    """

    userContent = [
        {
            "type": "text",
            "text": "Grade every question found across the attached answer script pages against the attached mark scheme."
        },
        {
            "type": "file",
            "file": {
                "filename": "mark_scheme.pdf",
                "file_data": markSchemeEncoded
            },
        },
    ]

    for encodedImg in answerImagesEncodedAarr:
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
                "Authorization": f"Bearer {apiKey}",
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
            timeout=120
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
        return False, f"Model didn't return Valid JSON: {e}. Raw Response: {content}"
    
    return True, resultJson