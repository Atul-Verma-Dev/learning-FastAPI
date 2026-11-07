from pydantic import BaseModel,Field

class Course(BaseModel):
    title:str = Field(min_length=3,max_length=100)
    credits:int = Field(gt=0,le=6)
    is_online:bool = False


@app.post("/courses")
def course(new_course:Course):
    return new_course

