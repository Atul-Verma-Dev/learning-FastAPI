from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/students/{student_id}")
def read_item(student_id: int, semester: str = "fall"):
    return {"student_id":student_id, "semester": semester}


