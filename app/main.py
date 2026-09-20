from fastapi import FastAPI

from app.database import Base, engine
from app.routers import batch, images

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Image Understanding & Content Matching Engine")

app.include_router(batch.router, tags=["batch"])
app.include_router(images.router, tags=["images"])


@app.get("/health")
def health():
    return {"status": "ok"}
