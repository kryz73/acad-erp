from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select
from core.database import engine, get_session
from models import schema
from strawberry.fastapi import GraphQLRouter
from auth.auth import router as auth_router, get_current_user
from typing import Annotated
from core.config import settings
from jose import jwt, JWTError
from models.identity import Users

app = FastAPI(title="AcadERP API")

# Allow the Next.js frontend to call the backend (including Vercel preview/production domains)
raw_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if "*" in raw_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=raw_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize database
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    # Automatically seed the database on initial deployment if empty
    try:
        with Session(engine) as session:
            first_user = session.exec(select(Users)).first()
            if not first_user:
                print("Database is empty. Automatically seeding initial demo data...")
                from seed_db import seed_db
                seed_db(drop_existing=False)
                print("Automatic seeding complete!")
    except Exception as e:
        print(f"Startup database check/seed notice: {e}")

# GraphQL context getter to provide database session and user info
async def get_context(request: Request, session: Session = Depends(get_session)):
    user_id = None
    roles = []
    user_dict = None
    
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = auth_header
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            candidate_id = payload.get('id')
            if candidate_id is not None:
                user = session.get(Users, candidate_id)
                if user and user.is_active:
                    user_id = user.id
                    roles = [link.role.name for link in user.role_links]
                    user_dict = {"id": user.id, "sub": user.email, "roles": roles}
        except JWTError:
            pass

    return {"session": session, "user_id": user_id, "roles": roles, "user": user_dict}

# Strawberry GraphQL Router
graphql_app = GraphQLRouter(schema, context_getter=get_context)

# Include Routers
app.include_router(auth_router)
app.include_router(graphql_app, prefix="/graphql")

# @app.get("/")
# async def root():
#     return {"message": "Welcome to AcadERP API"}


db_dependency = Annotated[Session, Depends(get_session)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.get("/", status_code=status.HTTP_200_OK)
async def user(user:user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication failed')
    return {'User': user}