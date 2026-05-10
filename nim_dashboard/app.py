from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.export.build_dashboard_data import ROOT, build_dashboard_data

app = FastAPI(title="Financial Closing Analytics Dashboard")

UPLOAD_DIR = ROOT / "uploads"
RAW_DIR = ROOT / "data" / "raw"
STATIC_DIR = ROOT / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/output", StaticFiles(directory=ROOT / "output"), name="output")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/upload")
async def upload_excel(file: UploadFile = File(...)):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / Path(file.filename).name
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    data = build_dashboard_data(ROOT)
    return JSONResponse({"uploaded": target.name, "available_months": data["status"]["available_months"]})


@app.post("/api/rebuild")
def rebuild():
    return build_dashboard_data(ROOT)


@app.get("/api/dashboard-data")
def dashboard_data():
    path = ROOT / "output" / "dashboard_data.json"
    if not path.exists():
        build_dashboard_data(ROOT)
    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn
    build_dashboard_data(ROOT)
    uvicorn.run("app:app", host="127.0.0.1", port=8601, reload=False)
