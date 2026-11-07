from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app:FastAPI):
    print("Server is starting....")
    x = {"connections":0}
    yield
    print("Server is shutting down....")

app = FastAPI(lifespan=lifespan)