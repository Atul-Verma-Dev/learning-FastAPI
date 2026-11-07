from fastapi import FastAPI

def verify_token(token:str):
    if token != "secret123":
        return False
    return True

@app.get("/protected")
def access(access_granted:bool = Depends(verify_token)):
    return {"access_granted":access_granted}