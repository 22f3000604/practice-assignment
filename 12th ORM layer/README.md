# Simple ORM Layer

A lightweight, asynchronous, thread-safe Object-Relational Mapping (ORM) library for Python. It interfaces with SQLite to provide dynamic model schema creation, type validation, async CRUD operations, and automatic parent-child relationship mappings.

## Features

- **Dynamic Schema Compilation**: Define model configurations in Python; the library compiles them and automatically builds the corresponding tables in SQLite.
- **Async Execution**: Database calls are executed on background threads using `asyncio.to_thread` to prevent synchronous blocking of the Python event loop.
- **Type and Constraint Validation**: Validates field inputs during creation, update, and dynamic property assignment (e.g. raises `ValidationError` on missing `required` properties or wrong types).
- **Auto Relationship Mapping**: 
  - **Forward Relationships**: Fetch parent records using `await child.get_<parent_model_name>()`.
  - **Reverse Relationships**: Fetch child record lists automatically using `await parent.get_<child_model_name>s()`.
- **Database Cascade Deletion**: Standard SQL constraint mapping so that deleting a parent record automatically deletes associated child records.
- **Concurrency & Thread Safety**: Uses thread locks and connection isolation to ensure concurrent execution of operations is safe.

## Installation & Setup

1. Verify Python 3.x is installed.
2. Initialize virtual environment, install requirements (`pytest`, `pytest-asyncio`), and run tests:
   ```bash
   # Set up virtual environment
   python3 -m venv .venv
   source .venv/bin/activate

   # Install test dependencies
   pip install pytest pytest-asyncio

   # Run tests
   pytest test_app.py -v
   ```

## Detailed Usage

### 1. Defining Models

Initialize models by passing the model name and a dictionary representing the schema.

```python
from app import model

# Define the User model
User = model('User', {
    'id': {'type': 'number', 'primary': True},
    'name': {'type': 'string', 'required': True},
    'email': {'type': 'string', 'unique': True}
})

# Define the Post model which references User
Post = model('Post', {
    'id': {'type': 'number', 'primary': True},
    'title': {'type': 'string', 'required': True},
    'userId': {'type': 'number', 'references': 'User'}
})
```

By default, an in-memory database (`:memory:`) is used. To write to a persistent SQLite file on disk, run:
```python
from app import configure_db
configure_db("my_app.db")
```

### 2. CRUD Operations

All operations are fully awaitable:

```python
# --- CREATE ---
user = await User.create({
    'name': 'John Doe',
    'email': 'john@example.com'
})
print(user.id)    # Primary key auto-populated (e.g. 1)
print(user.name)  # 'John Doe'

# --- FIND BY ID ---
# Supports both camelCase and snake_case
user = await User.findById(1)
user = await User.find_by_id(1)

# --- FIND WITH FILTERS ---
active_users = await User.find({'email': 'john@example.com'})

# --- UPDATE ---
updated = await User.update(user.id, {'name': 'Jane Doe'})
# Returns True on success, False if record not found

# --- DELETE ---
deleted = await User.delete(user.id)
# Returns True on success, False if record not found
```

### 3. Relationship Queries

Relations are automatically mapped and exposed via dynamic getters:

```python
user = await User.create({'name': 'Alice'})
post = await Post.create({'title': 'Hello World', 'userId': user.id})

# 1. Forward relationship (Child -> Parent)
# Method name matches: get_<parent_model_name_lowercase>()
author = await post.get_user()
print(author.name)  # 'Alice'

# 2. Reverse relationship (Parent -> Children)
# Method name matches: get_<child_model_name_lowercase>s()
posts = await user.get_posts()
print(len(posts))   # 1
print(posts[0].title)  # 'Hello World'
```
