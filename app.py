import requests, os

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

    fileName = f"{subjectCodeFormatted}_{shortenedCodeFormatted}_{fileTypeFormatted}_{variantFormatted}.pdf"

    downloadURL = f"{baseUrl}/download"

    currentDir = os.path.dirname(os.path.abspath(__file__))

    outputPath = os.path.join(currentDir, fileName)

    try:
        response = requests.get(downloadURL, headers=headers, stream=True)

        response.raise_for_status()

        with open(outputPath, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print(f"Successfully Fetched {fileName}. Saved at: {outputPath}")
    except Exception as e:
        print(f"An error occured: {e}")

# fetchFile("PhySiCs", "5054", "2025", "oct-nov", "w25", "11", fileType="Qp")