from pydantic import BaseModel,Field
from fastapi import FastAPI,HTTPException,BackgroundTasks

class CourseCreate(BaseModel):
    title:str
    credits:int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Course(Base):
    __tablename__ = "courses"
    id:Mapped[int] = mapped_column(primary_key=True)
    title:Mapped[str]
    credits:Mapped[int]



@app.post("/courses")
def create_course(course_data: CourseCreate, db = Depends(get_db)):
    new_course = Course(title=course_data.title, credits=course_data.credits)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return 
    

def log_action(message: str):
    print(message)

@app.get("/courses/{course_id}")
def show_course(course_id:int,background_tasks:BackgroundTasks,db = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404,"Course not found")
    else:
        background_tasks.add_task(log_action,f"Course {course_id} was viewed")
    return course

