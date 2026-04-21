import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

import fetcher
import exporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="DevOps Tools Version Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/versions")
async def get_versions():
    try:
        return await fetcher.fetch_all(force=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/versions/refresh")
async def refresh_versions():
    try:
        return await fetcher.fetch_all(force=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/export/csv")
async def export_csv():
    data = await fetcher.fetch_all(force=False)
    content = exporter.generate_csv(data)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=devops-versions.csv"},
    )


@app.get("/api/export/pdf")
async def export_pdf():
    data = await fetcher.fetch_all(force=False)
    content = exporter.generate_pdf(data)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=devops-versions.pdf"},
    )
