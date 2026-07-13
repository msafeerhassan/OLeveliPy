import requests, os
from pathlib import Path

example = "https://xtrapapers.co/papers/caie/o-level/physics-5054/2024-may-june/5054_s24_ms_12.pdf"

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

        print(f"Successfully Fetched {fileName}.")
    except Exception as e:
        print(f"An error occured: {e}")

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

        print(f"\nSubject: {subjectName}\nSubject Code: {subjectCode}\nExamination Year: {examinationYear}\nExamination Series: {formattedExamSeriesStr}\nExam Variant: {examVariant}\nFile Type: {fileType}\n")

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
            return True
        else:
            continue

    return False

# fetchFile("PhySiCs", "5054", "2025", "may-june", "s25", "11", fileType="qp")
# fetchFile("PhySiCs", "5054", "2025", "may-june", "s25", "12", fileType="ms")
# fetchFile("PhySiCs", "5054", "2024", "oct-nov", "w24", "11", fileType="qp")
# fetchFile("PhySiCs", "5054", "2024", "oct-nov", "w24", "12", fileType="ms")

# getAllPresentFiles("ms")
# getAllPresentFiles("qp")

if checkFilePresent("PhySiCs", "5054", "2023", "may-june", "s23", "11", fileType="qp"):
    print("Present file")
else:
    print("File Absent")