import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/test")
def test():
    return "GET"


@app.post("/test")
def test():
    return "POST"


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)
