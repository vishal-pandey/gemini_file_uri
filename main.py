import os
import uuid
import shutil
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware # Added
import google.generativeai as genai # Ensure this library is installed

# --- Configuration ---
# TODO: Configure the Google Generative AI SDK with your API key
# Example:
# genai.configure(api_key="YOUR_GEMINI_API_KEY")

# Define a temporary directory for uploads
TEMP_UPLOAD_DIR = "temp_gemini_uploads"

# Define allowed MIME types (customize as needed based on Gemini's supported types)
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'text/plain',
    'video/mp4', # Example: add video if supported and needed
    # Add other MIME types supported by Google Gemini API
    # Refer to Gemini API documentation for a comprehensive list
]

app = FastAPI(title="Gemini File Uploader API")

# Health / root endpoint
@app.get("/", tags=["health"])
async def health_root():
    return {"status": "ok"}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_event():
    # Create the temporary upload directory if it doesn't exist
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

@app.on_event("shutdown")
async def shutdown_event():
    # Optional: Clean up the temporary directory on shutdown
    # Be cautious with this in a production environment if multiple instances run
    # or if you need to inspect files post-mortem.
    # if os.path.exists(TEMP_UPLOAD_DIR):
    #     shutil.rmtree(TEMP_UPLOAD_DIR)
    pass


@app.post("/upload_to_gemini/")
async def upload_files_to_gemini(files: List[UploadFile] = File(...)):
    """
    Uploads one or more files to Google Gemini API and returns their URIs.
    """
    processed_files_details = []
    temp_file_paths = [] # Keep track of temp files for cleanup

    if not files:
        raise HTTPException(status_code=400, detail="No files were provided.")

    # Ensure the genai SDK is configured
    # Replace this with your actual API key or configuration method
    if not os.getenv("GOOGLE_API_KEY"): 
         print("Error: GOOGLE_API_KEY environment variable not set.")
         # You might want to call genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) here
         # or ensure it's done globally before the app starts.
         # For now, we'll raise an error if it's not set, assuming it should be.
         raise HTTPException(status_code=500, detail="Google Generative AI SDK not configured. Set GOOGLE_API_KEY environment variable.")
    else:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


    for file in files:
        temp_file_path = None  # Initialize for this iteration to avoid unbound reference in finally
        if file.content_type not in ALLOWED_MIME_TYPES:
            # Clean up any temp files created so far in this request before raising
            for temp_path in temp_file_paths:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type} for file '{file.filename}'. "
                       f"Supported types: {', '.join(ALLOWED_MIME_TYPES)}"
            )

        try:
            file_content = await file.read()
            if not file_content:
                # Clean up temp files
                for temp_path in temp_file_paths:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                raise HTTPException(status_code=400, detail=f"Uploaded file '{file.filename}' is empty.")

            # Create a unique temporary file path
            temp_file_path = os.path.join(TEMP_UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
            temp_file_paths.append(temp_file_path) # Add to list for cleanup

            with open(temp_file_path, "wb") as temp_f:
                temp_f.write(file_content)

            print(f"Uploading '{file.filename}' (MIME: {file.content_type}, Size: {len(file_content)} bytes) to Gemini...")
            
            # Upload the file to Google Gemini
            uploaded_file_response = genai.upload_file(
                path=temp_file_path,
                display_name=file.filename or f"upload_{uuid.uuid4()}", # Use original filename or a generated one
                mime_type=file.content_type
            )
            
            processed_files_details.append({
                "filename": file.filename,
                "uri": uploaded_file_response.uri,
                "gemini_filename": uploaded_file_response.name, # Gemini's internal name for the file
                "mime_type": uploaded_file_response.mime_type,
                "size_bytes": len(file_content) # Or from uploaded_file_response if available and preferred
            })
            print(f"File '{file.filename}' uploaded successfully. URI: {uploaded_file_response.uri}")

        except HTTPException: # Re-raise HTTPExceptions directly
            raise
        except Exception as e:
            print(f"Error processing file '{file.filename}': {e}")
            # Clean up temp files
            for temp_path in temp_file_paths:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"Error processing file '{file.filename}': {str(e)}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    if temp_file_path in temp_file_paths: # Remove from list if successfully deleted
                        temp_file_paths.remove(temp_file_path)
                except OSError as e:
                    print(f"Error deleting temporary file {temp_file_path}: {e}")

    if not processed_files_details:
        # This case might occur if all files failed individual processing steps
        # but didn't raise an exception that terminated the whole request early.
        raise HTTPException(status_code=500, detail="No files were successfully processed.")

    return {"uploaded_files": processed_files_details}

# To run this application (save as main.py or similar):
# 1. Install FastAPI and Uvicorn: pip install fastapi uvicorn google-generativeai
# 2. Set your GOOGLE_API_KEY environment variable or configure genai directly in the code.
# 3. Run Uvicorn: uvicorn main:app --reload
#
# Example curl command to test:
# curl -X POST -F "files=@/path/to/your/document1.pdf" -F "files=@/path/to/your/image1.png" http://127.0.0.1:8000/upload_to_gemini/
