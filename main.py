from fastapi import FastAPI, HTTPException

from database import check_database_connection

app = FastAPI(title="E-commerce API")


@app.get("/")
def root():
    return {"message": "Hello from FastAPI"}


@app.get("/health")
def health():
    try:
        check_database_connection()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "connected"}
