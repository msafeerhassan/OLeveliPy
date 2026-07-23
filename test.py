from app import pastPaperChecker, segmentAnswerScript, uploadToSupabase

status, result = fetchFile("PhySics", 5054, "2025", "may-june", "s25", "11", fileType="qp")
print(status, result)

print(checkFilePresent("PhySics", 5054, "2025", "may-june", "s25", "11", "qp"))