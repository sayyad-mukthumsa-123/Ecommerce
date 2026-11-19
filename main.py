from fastapi import FastAPI
from SQLAlchemy import create_engine


app = FastAPI(title="E-commerce API")


@app.get("/")
def root():
    return {"message": "Hello from FastAPI"}


engine = create_engine()