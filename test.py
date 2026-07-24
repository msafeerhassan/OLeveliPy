from app import fetchFile, uploadToSupabase, segmentAnswerScript, pastPaperChecker
from pathlib import Path

markSchemeStatus, markSchemePath = fetchFile("Physics", "5054", "2024", "may-june", "s24", "22", fileType="ms")

print("Mark Scheme Fetched: ", markSchemeStatus, markSchemePath)

dirPath = Path('test')
localImagePaths = []

for f in dirPath.iterdir():
    if f.is_file():
        localImagePaths.append(f)

uploadedImagePaths = []
failedUploads = []

for localPath in localImagePaths:
    with open(localPath, "rb") as f:
        status, storagePath = uploadToSupabase("answer-uploads", localPath.name, f.read(), "image/jpeg")
        print("Upload: ", localPath, status, storagePath)
        if status:
            uploadedImagePaths.append(storagePath)
        else:
            failedUploads.append((localPath, storagePath))

if failedUploads:
    print(f"\n{len(failedUploads)} uploads failed and were excluded from this run.")
    for path, error in failedUploads:
        print(f"    {path}: {error}")

segmentStatus, segmentResult = segmentAnswerScript(uploadedImagePaths)
print("\n Segmentation Status: ", segmentStatus)
print("Segmentation Result: ", segmentResult)

q3Images = [uploadedImagePaths[12], uploadedImagePaths[13]]


if markSchemeStatus:
    gradeStatus, gradeResult = pastPaperChecker(
        "Physics",
        "5054",
        "2024",
        "may-june",
        "22",
        questionNumber="3",
        markSchemePath=markSchemePath,
        answerImagesPath=q3Images
    )

    print("\nPast Paper Checker Status: ", gradeStatus)
    print("Past Paper Checker Result: ", gradeResult)