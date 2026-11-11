from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session
from core.database import engine, get_session
from models import schema
from strawberry.fastapi import GraphQLRouter
from auth.auth import router as auth_router, get_current_user
from typing import Annotated
from core.config import settings
from jose import jwt, JWTError
from models.identity import Users

app = FastAPI(title="AcadERP API")

# Allow the Next.js frontend to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000" , "http://localhost:5432"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

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