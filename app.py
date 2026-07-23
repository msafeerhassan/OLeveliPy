import requests, os, base64, json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

aiModel = "google/gemini-3.1-flash-lite"

supabaseUrl = os.getenv("SUPABASE_URL")
supabaseKey = os.getenv("SERVICE_ROLE_KEY")

if not supabaseUrl or not supabaseKey:
    raise RuntimeError("SUPABASE_URL and SERVICE_ROLE_KEY must be set in your environment variables file (.env)")

supabase: Client = create_client(supabaseUrl, supabaseKey)

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
        return False, e

def downloadFromSupabase(bucketName, filePath):
    try:
        fileBytes = supabase.storage.from_(bucketName).download(filePath)
        return True, fileBytes
    except Exception as e:
        return False, e

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