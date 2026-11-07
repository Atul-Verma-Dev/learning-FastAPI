from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()

# Point to your templates folder (next to this file)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


# ---------- Show the page ----------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home2.html", {"result": None})


# ---------- 1) GET: data arrives in the URL (query parameters) ----------
# The form sends:  /greet?name=Asha&age=25
@app.get("/greet", response_class=HTMLResponse)
def greet(request: Request, name: str, age: int):
    result = f"[GET] Hello {name}, you are {age}"
    return templates.TemplateResponse(request, "home2.html", {"result": result})


# ---------- 2) POST: data arrives in the request body (HTML form) ----------
# Needs:  pip install python-multipart
# Form() tells FastAPI to read the value from the form body, not the URL.
@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    age: Annotated[int, Form()],
):
    result = f"[POST] Registered {name} ({email}), age {age}"
    return templates.TemplateResponse(request, "home2.html", {"result": result})


# ---------- 3) POST: data arrives as JSON (sent by JavaScript fetch) ----------
class Student(BaseModel):
    name: str
    course: str


@app.post("/api/student")
def add_student(student: Student):
    return {"method": "POST (json)", "saved": student.model_dump()}