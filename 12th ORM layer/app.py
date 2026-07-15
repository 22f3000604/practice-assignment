import asyncio
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Type, Union


class ValidationError(ValueError):
    """Raised when validation on a model field fails."""
    pass


class IntegrityError(ValueError):
    """Raised when database unique/foreign key constraints fail."""
    pass


class DatabaseManager:
    """Thread-safe manager for SQLite database interactions."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.execute("PRAGMA foreign_keys = ON;")
            return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self.get_connection()
        with self._lock:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return cursor
            except sqlite3.IntegrityError as ie:
                raise IntegrityError(str(ie)) from ie
            except sqlite3.Error as e:
                raise ValueError(str(e)) from e

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        with self._lock:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            except sqlite3.Error as e:
                raise ValueError(str(e)) from e

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        with self._lock:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
            except sqlite3.Error as e:
                raise ValueError(str(e)) from e


# Global database manager context
_db_manager = DatabaseManager(db_path=":memory:")


def configure_db(db_path: str) -> None:
    """Configures the global SQLite database file path."""
    global _db_manager
    with _db_manager._lock:
        _db_manager.close()
        _db_manager = DatabaseManager(db_path)


# Registry to track defined models
_models_registry: Dict[str, 'Model'] = {}


def get_model(name: str) -> 'Model':
    """Looks up a registered model class by name."""
    if name not in _models_registry:
        raise ValueError(f"Model '{name}' is not registered.")
    return _models_registry[name]


def validate_field(name: str, value: Any, cfg: Dict[str, Any]) -> Any:
    """Validates field value against type and required configurations."""
    t = cfg.get('type')
    required = cfg.get('required', False)

    if value is None:
        if required and not cfg.get('primary'):
            raise ValidationError(f"Field '{name}' is required.")
        return None

    if t == 'string':
        if not isinstance(value, str):
            raise ValidationError(
                f"Field '{name}' must be a string, got {type(value).__name__}."
            )
    elif t == 'number':
        # In Python, bool is a subclass of int, so isinstance(True, int) is True.
        # We must explicitly exclude bool.
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(
                f"Field '{name}' must be a number, got {type(value).__name__}."
            )
    elif t == 'boolean':
        if not isinstance(value, bool):
            raise ValidationError(
                f"Field '{name}' must be a boolean, got {type(value).__name__}."
            )

    return value


class ModelInstance:
    """Represents a specific record row fetched from the database."""

    def __init__(self, model_class: 'Model', data: Dict[str, Any]) -> None:
        self.__dict__['_model_class'] = model_class
        self.__dict__.update(data)

        # Attach forward relationship getters (e.g. Post -> get_user())
        for field_name, field_cfg in model_class.fields.items():
            if 'references' in field_cfg:
                ref_model_name = field_cfg['references']
                ref_val = data.get(field_name)

                async def make_getter(val=ref_val, name=ref_model_name):
                    if val is None:
                        return None
                    ref_model = get_model(name)
                    return await ref_model.find_by_id(val)

                getter_name = f"get_{ref_model_name.lower()}"
                self.__dict__[getter_name] = make_getter

        # Attach reverse relationship getters (e.g. User -> get_posts())
        pk_field = model_class._pk_field
        pk_val = data.get(pk_field)

        for other_name, other_model in _models_registry.items():
            for other_field_name, other_field_cfg in other_model.fields.items():
                if other_field_cfg.get('references') == model_class.name:

                    async def make_list_getter(pk=pk_val, other_cls=other_model, fk=other_field_name):
                        if pk is None:
                            return []
                        return await other_cls.find({fk: pk})

                    getter_name = f"get_{other_model.name.lower()}s"
                    self.__dict__[getter_name] = make_list_getter

    def __setattr__(self, key: str, value: Any) -> None:
        if key in self._model_class.fields:
            self.__dict__[key] = validate_field(key, value, self._model_class.fields[key])
        else:
            self.__dict__[key] = value

    def __repr__(self) -> str:
        fields_repr = ", ".join(
            f"{k}={repr(v)}"
            for k, v in self.__dict__.items()
            if k in self._model_class.fields
        )
        return f"{self._model_class.name}({fields_repr})"

    def to_dict(self) -> Dict[str, Any]:
        """Converts model instance to a dictionary of field values."""
        return {
            k: v
            for k, v in self.__dict__.items()
            if k in self._model_class.fields
        }


class Model:
    """Compiles field schemas into SQL tables and handles CRUD operations."""

    def __init__(self, name: str, fields: Dict[str, Dict[str, Any]]) -> None:
        self.name = name
        self.fields = fields
        self.table_name = name.lower() + "s"

        # Determine Primary Key field
        self._pk_field = 'id'
        for k, v in fields.items():
            if v.get('primary'):
                self._pk_field = k
                break

        self._create_table()

    def _create_table(self) -> None:
        columns = []
        foreign_keys = []

        for name, cfg in self.fields.items():
            t = cfg.get('type')
            sql_type = 'TEXT'
            if t == 'number':
                sql_type = 'INTEGER'
            elif t == 'boolean':
                sql_type = 'INTEGER'

            col_def = f"{name} {sql_type}"

            if cfg.get('primary'):
                col_def += " PRIMARY KEY AUTOINCREMENT"
            else:
                if cfg.get('required'):
                    col_def += " NOT NULL"
                if cfg.get('unique'):
                    col_def += " UNIQUE"

            columns.append(col_def)

            if 'references' in cfg:
                ref_table = cfg['references'].lower() + "s"
                foreign_keys.append(
                    f"FOREIGN KEY({name}) REFERENCES {ref_table}(id) ON DELETE CASCADE"
                )

        sql_parts = columns + foreign_keys
        sql = f"CREATE TABLE IF NOT EXISTS {self.table_name} (\n  "
        sql += ",\n  ".join(sql_parts)
        sql += "\n);"

        _db_manager.execute(sql)

    # ---- CRUD API Methods (Thread-wrapped for Async Await) ----

    async def create(self, data: Dict[str, Any]) -> ModelInstance:
        """Asynchronously creates a record in the database."""
        return await asyncio.to_thread(self._create_sync, data)

    async def find(self, filters: Optional[Dict[str, Any]] = None) -> List[ModelInstance]:
        """Asynchronously searches records matching filter criteria."""
        return await asyncio.to_thread(self._find_sync, filters)

    async def find_by_id(self, pk_val: Any) -> Optional[ModelInstance]:
        """Asynchronously searches a record by its primary key ID."""
        return await asyncio.to_thread(self._find_by_id_sync, pk_val)

    async def findById(self, pk_val: Any) -> Optional[ModelInstance]:
        """Alias for find_by_id."""
        return await self.find_by_id(pk_val)

    async def update(self, pk_val: Any, data: Dict[str, Any]) -> bool:
        """Asynchronously updates a record by ID."""
        return await asyncio.to_thread(self._update_sync, pk_val, data)

    async def delete(self, pk_val: Any) -> bool:
        """Asynchronously deletes a record by ID."""
        return await asyncio.to_thread(self._delete_sync, pk_val)

    # ---- Sync CRUD Implementations ----

    def _create_sync(self, data: Dict[str, Any]) -> ModelInstance:
        validated_data = {}

        # Validate input fields and apply defaults
        for name, cfg in self.fields.items():
            if cfg.get('primary'):
                continue
            val = data.get(name)
            validated_data[name] = validate_field(name, val, cfg)

        # Build SQL INSERT query
        columns = list(validated_data.keys())
        placeholders = [f":{c}" for c in columns]
        sql = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        cursor = _db_manager.execute(sql, validated_data)
        last_id = cursor.lastrowid

        # Re-fetch or compile created fields
        full_data = dict(validated_data)
        if last_id is not None:
            full_data[self._pk_field] = last_id
        else:
            full_data[self._pk_field] = data.get(self._pk_field)

        return ModelInstance(self, full_data)

    def _find_sync(self, filters: Optional[Dict[str, Any]] = None) -> List[ModelInstance]:
        sql = f"SELECT * FROM {self.table_name}"
        params = {}

        if filters:
            where_clauses = []
            for k, v in filters.items():
                if k in self.fields:
                    where_clauses.append(f"{k} = :{k}")
                    params[k] = v
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

        rows = _db_manager.fetchall(sql, params)
        return [ModelInstance(self, row) for row in rows]

    def _find_by_id_sync(self, pk_val: Any) -> Optional[ModelInstance]:
        sql = f"SELECT * FROM {self.table_name} WHERE {self._pk_field} = ?"
        row = _db_manager.fetchone(sql, (pk_val,))
        if row:
            return ModelInstance(self, row)
        return None

    def _update_sync(self, pk_val: Any, data: Dict[str, Any]) -> bool:
        validated_data = {}

        # Validate fields
        for k, v in data.items():
            if k in self.fields and not self.fields[k].get('primary'):
                validated_data[k] = validate_field(k, v, self.fields[k])

        if not validated_data:
            return False

        set_parts = [f"{k} = :{k}" for k in validated_data.keys()]
        sql = f"UPDATE {self.table_name} SET {', '.join(set_parts)} WHERE {self._pk_field} = :_pk"

        params = dict(validated_data)
        params['_pk'] = pk_val

        cursor = _db_manager.execute(sql, params)
        return cursor.rowcount > 0

    def _delete_sync(self, pk_val: Any) -> bool:
        sql = f"DELETE FROM {self.table_name} WHERE {self._pk_field} = ?"
        cursor = _db_manager.execute(sql, (pk_val,))
        return cursor.rowcount > 0


def model(name: str, fields: Dict[str, Dict[str, Any]]) -> Model:
    """Factory to define and register a new Database Model."""
    if not name or not isinstance(name, str):
        raise ValueError("Model name must be a non-empty string.")
    if not isinstance(fields, dict):
        raise ValueError("Fields must be a dictionary.")

    # Register in global dictionary
    m = Model(name, fields)
    _models_registry[name] = m
    return m
