"""
Simple JWT authentication + SQLite user store.
Default admin: admin / admin123  (CHANGE THIS after first login!)
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

SECRET_KEY = os.environ.get("VALUATION_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "valuation.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'staff',
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS valuations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by TEXT,
            client_name TEXT,
            bank_name TEXT,
            branch TEXT,
            valuation_date TEXT,
            total_fmv INTEGER,
            total_distress INTEGER,
            request_json TEXT,
            result_json TEXT,
            created_at TEXT
        )
    """)
    # default admin
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES (?,?,?,?,?)",
            ("admin", pwd_context.hash("admin123"), "Administrator", "admin", datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


def save_valuation(username: str, req_dict: dict, result: dict):
    conn = get_db()
    cur = conn.cursor()
    import json
    cur.execute("""
        INSERT INTO valuations
        (created_by, client_name, bank_name, branch, valuation_date,
         total_fmv, total_distress, request_json, result_json, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        username,
        req_dict["client"]["client_name"],
        req_dict["bank_name"],
        req_dict["branch"],
        req_dict["valuation_date"],
        result["summary"]["total_fmv"],
        result["summary"]["total_distress"],
        json.dumps(req_dict),
        json.dumps({
            "summary": result["summary"],
            "plots": result["plots"],
            "building": result["building"],
        }),
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return vid


def list_valuations(limit: int = 50):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_by, client_name, bank_name, branch, valuation_date,
               total_fmv, total_distress, created_at
        FROM valuations ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
