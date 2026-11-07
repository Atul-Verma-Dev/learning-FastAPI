def get_fake_db():
    print("DB connection opened")
    try:
        yield "db_session"
    finally:
        print("DB connection closed")

@app.get("/use-db")
def db(session:str = Depends(get_fake_db)):
    return {"session":session}