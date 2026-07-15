import asyncio
import pytest
from app import (
    IntegrityError,
    ValidationError,
    _models_registry,
    configure_db,
    get_model,
    model,
)


@pytest.fixture(autouse=True)
def clean_db():
    """Wipes the models registry and sets up a fresh in-memory database before each test."""
    _models_registry.clear()
    configure_db(":memory:")
    yield


# ---- Model Definition & Schema compilation Tests ----


def test_model_definition():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string', 'required': True},
        'email': {'type': 'string', 'unique': True},
        'isAdmin': {'type': 'boolean'}
    })

    assert User.name == 'User'
    assert User.table_name == 'users'
    assert User._pk_field == 'id'
    assert get_model('User') == User


# ---- Validation Tests ----


@pytest.mark.asyncio
async def test_validation_required_fields():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string', 'required': True}
    })

    # Missing name (required)
    with pytest.raises(ValidationError, match="Field 'name' is required"):
        await User.create({})


@pytest.mark.asyncio
async def test_validation_data_types():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string'},
        'age': {'type': 'number'},
        'active': {'type': 'boolean'}
    })

    # Invalid name (expects string)
    with pytest.raises(ValidationError, match="must be a string"):
        await User.create({'name': 123})

    # Invalid age (expects number)
    with pytest.raises(ValidationError, match="must be a number"):
        await User.create({'name': 'John', 'age': '25'})

    # Invalid age (expects number, passing bool which is disallowed)
    with pytest.raises(ValidationError, match="must be a number"):
        await User.create({'name': 'John', 'age': True})

    # Invalid active (expects boolean)
    with pytest.raises(ValidationError, match="must be a boolean"):
        await User.create({'name': 'John', 'active': 1})


@pytest.mark.asyncio
async def test_validation_on_instance_setattr():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string'}
    })

    user = await User.create({'name': 'John'})
    assert user.name == 'John'

    user.name = 'Jane'
    assert user.name == 'Jane'

    with pytest.raises(ValidationError, match="must be a string"):
        user.name = 123


# ---- CRUD Tests ----


@pytest.mark.asyncio
async def test_crud_lifecycle():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string', 'required': True},
        'email': {'type': 'string', 'unique': True}
    })

    # 1. Create
    user = await User.create({'name': 'John Doe', 'email': 'john@example.com'})
    assert user.id is not None
    assert user.name == 'John Doe'
    assert user.email == 'john@example.com'

    # 2. Find by ID (snake_case and camelCase)
    found = await User.find_by_id(user.id)
    assert found is not None
    assert found.name == 'John Doe'

    found_camel = await User.findById(user.id)
    assert found_camel is not None
    assert found_camel.email == 'john@example.com'

    # 3. Find with filters
    users = await User.find({'name': 'John Doe'})
    assert len(users) == 1
    assert users[0].id == user.id

    no_users = await User.find({'name': 'Unknown'})
    assert len(no_users) == 0

    # 4. Update
    updated = await User.update(user.id, {'name': 'Jane Doe'})
    assert updated is True

    refetched = await User.find_by_id(user.id)
    assert refetched.name == 'Jane Doe'
    assert refetched.email == 'john@example.com'  # Unchanged field is preserved

    # 5. Delete
    deleted = await User.delete(user.id)
    assert deleted is True

    post_delete = await User.find_by_id(user.id)
    assert post_delete is None


# ---- Database Unique Constraints Tests ----


@pytest.mark.asyncio
async def test_unique_constraint():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'email': {'type': 'string', 'unique': True}
    })

    await User.create({'email': 'john@example.com'})

    # Duplicate email insert
    with pytest.raises(IntegrityError):
        await User.create({'email': 'john@example.com'})


# ---- Relationship Tests ----


@pytest.mark.asyncio
async def test_model_relationships():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string', 'required': True}
    })

    Post = model('Post', {
        'id': {'type': 'number', 'primary': True},
        'title': {'type': 'string', 'required': True},
        'userId': {'type': 'number', 'references': 'User'}
    })

    user = await User.create({'name': 'Author'})
    post1 = await Post.create({'title': 'Post 1', 'userId': user.id})
    post2 = await Post.create({'title': 'Post 2', 'userId': user.id})

    # Forward relationship (Post -> get_user())
    author = await post1.get_user()
    assert author is not None
    assert author.id == user.id
    assert author.name == 'Author'

    # Reverse relationship (User -> get_posts())
    posts = await user.get_posts()
    assert len(posts) == 2
    titles = [p.title for p in posts]
    assert 'Post 1' in titles
    assert 'Post 2' in titles


@pytest.mark.asyncio
async def test_relationship_cascade_delete():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string', 'required': True}
    })

    Post = model('Post', {
        'id': {'type': 'number', 'primary': True},
        'title': {'type': 'string', 'required': True},
        'userId': {'type': 'number', 'references': 'User'}
    })

    user = await User.create({'name': 'Author'})
    await Post.create({'title': 'Post 1', 'userId': user.id})

    # Verify posts exist
    posts_before = await Post.find({'userId': user.id})
    assert len(posts_before) == 1

    # Delete parent user
    await User.delete(user.id)

    # Verify child posts were deleted by cascade
    posts_after = await Post.find({'userId': user.id})
    assert len(posts_after) == 0


# ---- Concurrency Tests ----


@pytest.mark.asyncio
async def test_concurrent_db_operations():
    User = model('User', {
        'id': {'type': 'number', 'primary': True},
        'name': {'type': 'string', 'required': True}
    })

    # Spawn multiple operations concurrently
    tasks = [
        User.create({'name': f"User {i}"})
        for i in range(10)
    ]
    instances = await asyncio.gather(*tasks)
    assert len(instances) == 10
    for idx, inst in enumerate(instances):
        assert inst.name == f"User {idx}"
        assert inst.id is not None

    users = await User.find()
    assert len(users) == 10
