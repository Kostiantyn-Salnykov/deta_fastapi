import uuid
from typing import Optional

from deta import Deta
from deta.base import FetchResponse
from fastapi import FastAPI, Response, status, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from settings import Settings

deta = Deta(project_key=Settings.PROJECT_KEY, project_id=Settings.PROJECT_ID)
db = deta.Base(name="todos")
files_metadata = deta.Base(name="files_metadata")
drive = deta.Drive(name="files")
app = FastAPI(debug=True, title="Deta ToDo app")
todos_router = APIRouter(prefix="/todos", tags=["todos"])
file_router = APIRouter(prefix="/files", tags=["files"])


def generate_key() -> str:
    return str(uuid.uuid1())


class ToDoInSchema(BaseModel):
    title: str = Field(max_length=128)
    description: Optional[str] = Field(max_length=128)


class ToDoUpdateInSchema(BaseModel):
    title: Optional[str] = Field(max_length=128)
    description: Optional[str] = Field(max_length=128)


class ToDoOutSchema(BaseModel):
    key: str = Field(default_factory=generate_key)
    title: str = Field(max_length=128)
    description: Optional[str] = Field(max_length=128)


@app.get("/", status_code=status.HTTP_200_OK, summary="Health Check")
async def healthcheck():
    return {"Hello": "World"}


@todos_router.post(path="/", status_code=status.HTTP_201_CREATED, response_model=ToDoOutSchema)
async def create_todo(data: ToDoInSchema) -> JSONResponse:
    result_data = ToDoOutSchema(**data.dict())
    db.insert(data=data.dict(), key=result_data.key)
    return JSONResponse(content=result_data.dict(), status_code=status.HTTP_201_CREATED)


@todos_router.get("/", status_code=status.HTTP_200_OK, response_model=list[ToDoOutSchema])
async def read_todos() -> JSONResponse:
    fetch_response: FetchResponse = db.fetch()
    return JSONResponse(content=fetch_response.items, status_code=status.HTTP_200_OK)


@todos_router.get("/{key}/", status_code=status.HTTP_200_OK, response_model=ToDoOutSchema)
async def read_todo(key: str) -> ToDoOutSchema:
    return db.get(key=key)


@todos_router.patch("/{key}/", status_code=status.HTTP_200_OK)
def update_todo(key: str, data: ToDoUpdateInSchema):
    try:
        db.update(updates=data.dict(exclude_unset=True), key=key)
        return db.get(key=key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ToDo not found.")


@todos_router.delete("/{key}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(key: str):
    db.delete(key=key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@file_router.post(path="/")
async def upload_file(file: UploadFile = File(...)):
    res = drive.put(name=file.filename, data=file.file, content_type=file.content_type)
    data = {"media_type": file.content_type, "filename": file.filename}
    print(data)
    files_metadata.insert(data=data, key=file.filename)
    return res


@file_router.get("/retrieve/{name}")
async def retrieve_file(name: str):
    res = drive.get(name=name)
    file_metadata = files_metadata.get(key=name)
    return StreamingResponse(content=res.iter_chunks(chunk_size=1024), media_type=file_metadata["media_type"])


@file_router.get("/download/{name}")
async def download_file(name: str):
    res = drive.get(name=name)
    file_metadata = files_metadata.get(key=name)
    return StreamingResponse(
        content=res.iter_chunks(chunk_size=1024),
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
        media_type=file_metadata["media_type"]
    )


@file_router.delete(path="/{name}")
async def delete_file(name: str):
    res = drive.delete(name=name)
    files_metadata.delete(key=name)
    return res


@file_router.get("/")
async def list_filenames():
    return drive.list()["names"]


app.include_router(router=todos_router)
app.include_router(router=file_router)
