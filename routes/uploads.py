from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from config.config import TEMP_DIR
from services.interview_state import interview_state

# Create router instance
router = APIRouter(
    prefix="/upload",
    tags=["uploads"]
)

@router.post("/resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        file_path = TEMP_DIR / "resume" / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        interview_state.resume_path = file_path
        return JSONResponse(content={"status": "success", "path": str(file_path)})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/jd")
async def upload_jd(file: UploadFile = File(...)):
    try:
        file_path = TEMP_DIR / "jd" / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        interview_state.jd_path = file_path
        return JSONResponse(content={"status": "success", "path": str(file_path)})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

