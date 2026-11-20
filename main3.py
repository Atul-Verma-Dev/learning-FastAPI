from fastapi import FastAPI, Request,Response,BackgroundTasks,HTTPException
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
import html
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import time

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

def send_smtp_otp(to_email: str, session_id):
    code = str(secrets.randbelow(90000) + 10000)
    z[session_id]["code"] = code
    z[session_id]["expires_at"] = time.time() + 300   # 5 minutes
    z[session_id]["attempts"] = 0
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your Sync Code: {code}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(f"<p>Your verification code is: <b>{code}</b></p>", "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

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

    if session_id not in z:             
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
async def get_email_id(email: email_input, background_tasks: BackgroundTasks, request: Request, response: Response):
    x = get_or_set_session_id(request, response)
    z[x]["sends"] = z[x].get("sends", 0) + 1
    if z[x]["sends"] > 3:
        return {"Status": "Limit"}
    z[x]["email"] = email.email_id
    background_tasks.add_task(send_smtp_otp, email.email_id, x)
    return {"Status": "Sent"}

class otp_js(BaseModel):
    otp:str

@app.post("/api/code")
def rec_code_from_js(otp: otp_js, request: Request, response: Response):
    x = get_or_set_session_id(request, response)
    s = z[x]
    print("typed:", repr(otp.otp), "stored:", repr(s.get("code")))
    if s.get("attempts", 0) >= 5:
        return {"Status": "Locked"}
    if time.time() > s.get("expires_at", 0):
        return {"Status": "Expired"}
    if otp.otp.strip() == s.get("code"):
        s["status"] = 1
        conn = p.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("UPDATE Data SET email_or_uuid = %s WHERE email_or_uuid = %s", (s.get("email"), x))
        conn.commit()
        cur.close()
        conn.close()
        s["verification_status"] = "Verified"
        return {"Status": "Verified"}
    s["attempts"] = s.get("attempts", 0) + 1
    return {"Status": "Wrong", "left": 5 - s["attempts"]}


@app.get("/api/verified")
async def verif(request:Request,response:Response):
    x = get_or_set_session_id(request,response)
    if z.get(x).get("verification_status") == "Verified":
        return{"Status":"Verified"}
    elif z.get(x).get("verification_status") == "Unverified":
        return{"Status":"Not Verified"}
# class person(BaseModel):
#     main_type:str
#     title:str
#     task_type:str|None=None
#     subject:str|None=None
#     cert_desc:str|None=None
#     deadline:datetime

class primary_key(BaseModel):
    task_id:str

@app.post("/api/update")
def recieve_id(id:primary_key,request:Request,response:Response):
    x = get_or_set_session_id(request,response)
    y = id.task_id
    z[x]["id"] = y
    conn = p.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT id,type,title,task_type,subject,description,deadline FROM Data WHERE id=%s",(y,))
    result = cur.fetchone()
    data = list(result)
    data[6] = result[6].strftime("%Y-%m-%dT%H:%M") if result[6] else ""
    cur.close()
    conn.close()
    return {"data":data}

class user_task(BaseModel):#Data filled earlier by user
    id:int
    type:str
    title:str
    task_type:str|None=None
    subject:str|None=None
    description:str|None=None
    deadline:datetime

                                         

@app.post("/api/update_db")
def update_db(data:user_task,request:Request,response:Response):
    x = get_or_set_session_id(request,response)
    conn = p.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    # if z.get(x).get("status") == 0:
    #         cur.execute("SELECT id,type,title,task_type,subject,description,deadline FROM Data WHERE email_or_uuid=%s",(x,))
    #     elif z.get(x).get("status") == 1:
    #         cur.execute("SELECT id,type,title,task_type,subject,description,deadline FROM Data WHERE email_or_uuid=%s",(z.get(x).get("email"),))
    if z.get(x).get("status") == 0:
        cur.execute("UPDATE Data SET type = %s,title = %s,task_type = %s,subject = %s,description = %s,deadline = %s WHERE id = %s AND email_or_uuid = %s",(data.type,data.title,data.task_type,data.subject,data.description,data.deadline,data.id,x))
    elif z.get(x).get("status") == 1:
        cur.execute("UPDATE Data SET type = %s,title = %s,task_type = %s,subject = %s,description = %s,deadline = %s WHERE id = %s AND email_or_uuid = %s",(data.type,data.title,data.task_type,data.subject,data.description,data.deadline,data.id,z.get(x).get("email")))
    conn.commit()
    cur.close()
    conn.close()
    return {"Status":"Updated"}


@app.post("/api/delete")
def delete(id:primary_key,request:Request,response:Response):
    x = get_or_set_session_id(request,response)
    conn = p.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    if z.get(x).get("status") == 0:
        cur.execute("DELETE FROM Data WHERE id = %s AND email_or_uuid = %s",(id.task_id,x))
    elif z.get(x).get("status") == 1:
        cur.execute("DELETE FROM Data WHERE id = %s AND email_or_uuid = %s",(id.task_id,z.get(x).get("email")))
    conn.commit()
    cur.close()
    conn.close()


class Feedback(BaseModel):
    name: str
    email: str
    category: str = "General"
    rating: str | None = None
    message: str


def send_feedback_email(feedback: Feedback):
    """Turn a feedback form submission into an email and send it to the owner."""
    rating = f"{feedback.rating}/5" if feedback.rating else "Not rated"
    safe_name = feedback.name.replace("\r", " ").replace("\n", " ")
    safe_category = feedback.category.replace("\r", " ").replace("\n", " ")
    safe_email = feedback.email.replace("\r", "").replace("\n", "")

    text_body = (
        "New feedback received from the Dhyan-CERT & Study Tracker site\n\n"
        f"Name:     {feedback.name}\n"
        f"Email:    {feedback.email}\n"
        f"Category: {feedback.category}\n"
        f"Rating:   {rating}\n\n"
        f"Message:\n{feedback.message}\n"
    )

    html_body = f"""
    <div style="font-family: system-ui, sans-serif; color: #111; line-height: 1.6;">
        <h2 style="margin: 0 0 16px;">New Feedback Received</h2>
        <table style="border-collapse: collapse;">
            <tr><td style="padding: 4px 12px 4px 0;"><strong>Name</strong></td><td>{html.escape(feedback.name)}</td></tr>
            <tr><td style="padding: 4px 12px 4px 0;"><strong>Email</strong></td><td>{html.escape(feedback.email)}</td></tr>
            <tr><td style="padding: 4px 12px 4px 0;"><strong>Category</strong></td><td>{html.escape(feedback.category)}</td></tr>
            <tr><td style="padding: 4px 12px 4px 0;"><strong>Rating</strong></td><td>{html.escape(rating)}</td></tr>
        </table>
        <h3 style="margin: 20px 0 8px;">Message</h3>
        <p style="white-space: pre-wrap; margin: 0;">{html.escape(feedback.message)}</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New Feedback: {safe_category} - {safe_name}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = SENDER_EMAIL
    msg["Reply-To"] = safe_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [SENDER_EMAIL], msg.as_string())


@app.post("/api/feedback")
def submit_feedback(feedback: Feedback):
    if not feedback.name.strip() or not feedback.email.strip() or not feedback.message.strip():
        raise HTTPException(status_code=400, detail="Name, email and message are required.")
    if "@" not in feedback.email or "." not in feedback.email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    try:
        send_feedback_email(feedback)
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(status_code=502, detail="Could not send feedback email. Please try again later.") from exc

    return {"Status": "Sent"}

