from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from . import models, schemas, auth
from .database import engine, get_db, Base

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="user-service")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda r, e: HTTPException(status_code=429, detail="Too many requests"))
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev ke liye; production mein specific origin (dashboard URL) daalna
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.post("/api/signup", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
async def signup(request: Request, user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        email=user.email,
        hashed_password=auth.hash_password(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = auth.create_access_token({"sub": str(new_user.id)})
    return {"access_token": token}


@app.post("/api/login", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, user: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    db_user = result.scalar_one_or_none()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token}


@app.get("/health")
async def health():
    return {"status": "ok"}