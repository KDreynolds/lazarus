from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import boto3
import time
import os
import re 

app = FastAPI()
load_dotenv()

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_KEY")
bucket_name = os.getenv("BUCKET_NAME")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

s3 = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
objects = s3.list_objects(Bucket=bucket_name)
ongoing_process = None
log_directory = Path("/logs")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>FastAPI Upload</title>
        </head>
        <body>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file">
                <input type="submit">
            </form>
        </body>
    </html>
    """


@app.post("/upload")
async def upload_file(file: UploadFile):
    global ongoing_process
    
    # Define and create the temporary upload directory if it doesn’t exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filename = upload_dir / file.filename
    
    try:
        # Write the file to the temporary directory
        with filename.open("wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file locally: {str(e)}")
    
    # Correctly format the rclone destination with the actual bucket name
    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="BUCKET_NAME environment variable is not set")
    rclone_destination = f'rclone-javascript-bucket:{bucket_name}' # corrected to use variable bucket_name
    
    # Set log file
    log_directory.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    log_file = log_directory / f"rclone_log_{timestamp}.txt"
    
    try:
        # Modified subprocess.Popen call to correctly pass the parameters
        ongoing_process = subprocess.Popen(["rclone", "copy", "--progress", "--log-file", str(log_file), str(filename), rclone_destination])
        ongoing_process.wait()
        
        # Check for errors from the subprocess (non-zero return code)
        if ongoing_process.returncode != 0:
            raise Exception("rclone copy returned non-zero exit code.")
        
        os.remove(filename)
        return {"status": "success", "message": "File uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in uploading file to s3: {str(e)}")


@app.get("/status")
async def get_status():
    try:
        response = s3.list_objects_v2(bucket_name)
        if 'Contents' in response:
            files = [content['Key'] for content in response['Contents']]
            return {"status": "success", "files": files}
        else:
            return {"status": "success", "message": "No files found in the bucket"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/stop")
async def stop_upload():
    global ongoing_process
    if ongoing_process is not None:
        ongoing_process.terminate()
        ongoing_process = None
        return {"status": "success", "message": "Upload stopped successfully"}
    else:
        return {"status": "error", "message": "No ongoing upload to stop"}
    


########## Log Parsing ##########

def get_latest_log_file(log_directory):
    try:
        return max(
            (log_directory / f for f in os.listdir(log_directory) if f.endswith('.txt')),
            key=os.path.getctime
        )
    except ValueError:
        return None


def parse_logs(log_file):
    with open(log_file, 'r') as file:
        logs = file.read()
        progress_info = re.findall('some_regular_expression', logs)
        return progress_info
    

def background_task():
    while True:
        log_file = get_latest_log_file(log_directory)
        if log_file:
            progress_info = parse_logs(log_file)
        time.sleep(1)
