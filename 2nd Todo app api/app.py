# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime


app = FastAPI()


# ---- Pydantic Models (for input validation) ----

class TodoCreate(BaseModel):
    name: str
    description: str = ""

class TodoUpdate(BaseModel):
    name: str = None
    description: str = None
    completed: bool = None    






class TodoCreate(BaseModel):
    name: str
    description: str = ""

class TodoUpdate(BaseModel):
    name: str = None
    description: str = None
    completed: bool = None


# ---- In-Memory Storage ----

todos = [
    {"id": 1,
     "name": "Study Machine Learning",
     "description": "linear regression study",
     "completed": False,
     "timestamp": datetime.now().isoformat()},
    {"id":2,
     "name": "Do Exercise",
     "description": "go for a walk",
     "completed":False,
     "timestamp":datetime.now().isoformat()},

    {"id":3,
     "name": "call my mom",
     "description": "",
     "completed":False,
     "timestamp":datetime.now().isoformat()}
]

id_counter = 1  # tracks the last used id


# ---- Helper Function ----

def find_todo(todo_id: int):
    for todo in todos:
        if todo["id"] == todo_id:
            return todo
    return None


# ---- GET: List all todos ----

@app.get("/todos")
def get_todos():
    return todos

# ---- GET: Get a specific todo ----

@app.get("/todos/{todo_id}")
def get_todo(todo_id:int):
    for todo in todos:
        if todo["id"] == todo_id:
            return todo
    raise HTTPException(status_code = 404, detail="Todo not found")


# ---- POST: Create a new todo ----

@app.post("/todos", status_code=201)
def create_todo(todo_data: TodoCreate):
    global id_counter
    id_counter+=1
    
    new_todo = {
        "id":id_counter,
        "name":todo_data.name,
        "description":todo_data.description,
        "completed":False,
        "timestamp":datetime.now().isoformat()
    }


    todos.append(new_todo)
    return new_todo



# ---- PUT: Update an existing todo ----

@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo_data: TodoUpdate):
    todo = find_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    if todo_data.name is not None:
        todo["name"] = todo_data.name
    if todo_data.description is not None:
        todo["description"] = todo_data.description
    if todo_data.completed is not None:
        todo["completed"] = todo_data.completed

    return todo


# ---- DELETE: Delete a todo ----

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    todo = find_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    todos.remove(todo)
    return {"message": f"Todo '{todo['name']}' deleted successfully"}