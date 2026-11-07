from fastapi import FastAPI, Request,Response,BackgroundTasks
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Literal
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
import os
import psycopg2 as p
import uuid
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

app = FastAPI()


load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
app.mount("/static", StaticFiles(directory="static"), name="static")


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "av1672206@gmail.com"
SENDER_PASSWORD = APP_PASSWORD 

z = {}

def send_smtp_otp(to_email: str,session_id):
    msg = MIMEMultipart("alternative")
    code = str(secrets.randbelow(90000)+10000)
    msg["Subject"] = f"Your Sync Code: {code}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    html_content = f"<p>Your verification code is: <b>{code}</b></p>"
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()  # Secure connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
    z[session_id]["code"] = code

templates = Jinja2Templates(directory="templates")

conn = p.connect(DATABASE_URL, connect_timeout=10)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS Data(id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,email_or_uuid VARCHAR(500),type VARCHAR(20),title VARCHAR(500),task_type VARCHAR(20),subject VARCHAR(500),description TEXT,deadline TIMESTAMP)")
conn.commit()
cur.close()
conn.close()

class Choice(BaseModel):
    value: Literal["Nothing", "Academia", "Certification", "Chore", "Other"]



def get_or_set_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get("session_id")

    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 365
        )

    if session_id not in z:              # add these two lines
        z[session_id] = {"status": 0}

    return session_id



@app.post("/api/student")
def get_choice(choice: Choice):
    print(choice.value)
    return {"received": choice.value}

class person(BaseModel):
    main_type:str
    title:str
    task_type:str|None=None
    subject:str|None=None
    cert_desc:str|None=None
    deadline:datetime




@app.get("/", response_class=HTMLResponse)
async def home(request: Request,response:Response):
    get_or_set_session_id(request,response)
    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )

@app.post("/api/person")
def data(person:person,request: Request,response:Response):
    x = get_or_set_session_id(request,response)
    d={"main_type":person.main_type,"title":person.title,"task_type":person.task_type,"subject":person.subject,"desc":person.cert_desc,"date":person.deadline}
    conn = p.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    if z.get(x).get("status") == 0:
        cur.execute("INSERT INTO Data(email_or_uuid,type,title,task_type,subject,description,deadline) VALUES(%s,%s,%s,%s,%s,%s,%s)",(x,d["main_type"],d["title"],d["task_type"],d["subject"],d["desc"],d["date"]))
    elif z.get(x).get("status") == 1:
        cur.execute("INSERT INTO Data(email_or_uuid,type,title,task_type,subject,description,deadline) VALUES(%s,%s,%s,%s,%s,%s,%s)",(z[x].get("email"),d["main_type"],d["title"],d["task_type"],d["subject"],d["desc"],d["date"]))
    conn.commit()
    cur.close()
    conn.close()
    return {"main_type":person.main_type,"title":person.title,"task_type":person.task_type,"subject":person.subject,"desc":person.cert_desc,"date":person.deadline}


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html"
    )


@app.get("/feedback", response_class=HTMLResponse)
async def feedback(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="feedback.html"
    )


@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request,response:Response):
    x = get_or_set_session_id(request,response)
    conn = p.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    if z.get(x).get("status") == 0:
        cur.execute("SELECT id,type,title,task_type,subject,description,deadline FROM Data WHERE email_or_uuid=%s",(x,))
    elif z.get(x).get("status") == 1:
        cur.execute("SELECT id,type,title,task_type,subject,description,deadline FROM Data WHERE email_or_uuid=%s",(z.get(x).get("email"),))
    tasks = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    response_to = templates.TemplateResponse(
        request=request,
        name="task-list.html",
        context={"tasks": tasks}
    )
    return response_to

class email_input(BaseModel):
    email_id:str

@app.post("/api/email_id")
async def get_email_id(email:email_input,background_tasks: BackgroundTasks,request: Request,response:Response):
    x = get_or_set_session_id(request,response)
    y = email.email_id
    z[x]["email"] = y
    background_tasks.add_task(send_smtp_otp,y,x)
    return y

class otp_js(BaseModel):
    otp:str

@app.post("/api/code")
def rec_code_from_js(otp:otp_js,request: Request,response:Response):
    x = get_or_set_session_id(request,response)
    if otp.otp == z.get(x).get("code"):
        z[x]["status"] = 1
        conn = p.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("UPDATE Data SET email_or_uuid = %s WHERE email_or_uuid = %s",(z.get(x).get("email"),x))
        conn.commit()
        cur.close()
        conn.close()
        return{"Status":"Verified"}
    else:
        return{"Status":"Not Verified"}
    


@app.get("api/update")
def 