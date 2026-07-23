from app import uploadToSupabase, downloadFromSupabase, checkExistInSupabase

status, result = uploadToSupabase("mark-schemes", "test.txt", b"Hello World", "text/plain")

print(status, result)

print(checkExistInSupabase("mark-schemes", "test.txt"))

status, data = downloadFromSupabase("mark-schemes", "test.txt")

print(status, data)