import os
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from calculator.finance_tools import batch_summarize, summarize_csv_column


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = FastAPI(title="Backend Foundations API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    destination = UPLOAD_FOLDER / file.filename
    content = await file.read()

    with destination.open("wb") as file_handle:
        file_handle.write(content)

    return {
        "filename": file.filename,
        "path": str(destination),
        "size": len(content),
    }


@app.get("/summary")
def get_summary(file: str, column: str):
    path = os.path.join(UPLOAD_FOLDER, file)

    if not os.path.exists(path):
        return {"error": "File not found"}

    try:
        result = summarize_csv_column(path, column)
        return result
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/batch-summary")
def batch_summary(folder: str, column: str):
    if not os.path.exists(folder):
        return {"error": "Folder not found"}

    try:
        results, total = batch_summarize(folder, column)
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "files": [{"file": file_name, "total": total_value} for file_name, total_value in results],
        "grand_total": total,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("ENV", "development").lower() != "production"

    uvicorn.run("calculator.api:app", host=host, port=port, reload=reload_enabled)
