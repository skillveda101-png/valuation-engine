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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS site_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_uid TEXT UNIQUE NOT NULL,
            created_by TEXT,
            client_name TEXT NOT NULL,
            plot_no TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            branch TEXT NOT NULL,
            gps_lat REAL,
            gps_lng REAL,
            gps_accuracy REAL,
            gps_text TEXT,
            notes TEXT,
            photo_paths TEXT,
            visited_at TEXT,
            synced_at TEXT,
            used_in_report_id TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE,
            created_by TEXT,
            client_name TEXT,
            plot_nos TEXT,
            bank_name TEXT,
            branch TEXT,
            total_fmv REAL,
            total_distress REAL,
            valuation_date TEXT,
            pdf_path TEXT,
            site_visit_ids TEXT,
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


def ensure_reports_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            username TEXT,
            client_name TEXT,
            owner_name TEXT,
            bank_name TEXT,
            branch TEXT,
            plot_nos TEXT,
            total_fmv REAL,
            total_distress REAL,
            valuation_date TEXT,
            content_hash TEXT,
            payload_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_report_record(report_id: str, username: str, req: dict, summary: dict, content_hash: str):
    ensure_reports_table()
    import json
    from datetime import datetime
    plots = req.get("plots") or []
    plot_nos = ", ".join(str(p.get("plot_no", "")) for p in plots)
    client = req.get("client") or {}
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO reports
           (id, created_at, username, client_name, owner_name, bank_name, branch,
            plot_nos, total_fmv, total_distress, valuation_date, content_hash, payload_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            report_id,
            datetime.utcnow().isoformat() + "Z",
            username,
            client.get("client_name", ""),
            client.get("owner_name", ""),
            req.get("bank_name", ""),
            req.get("branch", ""),
            plot_nos,
            summary.get("total_fmv", 0),
            summary.get("total_distress", 0),
            req.get("valuation_date", ""),
            content_hash,
            json.dumps({"summary": summary, "bank": req.get("bank_name"), "plots": plot_nos}),
        ),
    )
    conn.commit()
    conn.close()


def get_report_record(report_id: str):
    ensure_reports_table()
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


# ---------- Site visits & PDF records ----------

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "data", "photos")
PDFS_DIR = os.path.join(os.path.dirname(__file__), "data", "pdfs")


def ensure_storage_dirs():
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    os.makedirs(PDFS_DIR, exist_ok=True)


def save_site_visit(
    visit_uid: str,
    username: str,
    client_name: str,
    plot_no: str,
    bank_name: str,
    branch: str,
    gps_lat: Optional[float],
    gps_lng: Optional[float],
    gps_accuracy: Optional[float],
    gps_text: str,
    notes: str,
    photo_paths: list,
    visited_at: str,
) -> dict:
    import json
    ensure_storage_dirs()
    conn = get_db()
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """INSERT OR REPLACE INTO site_visits
           (visit_uid, created_by, client_name, plot_no, bank_name, branch,
            gps_lat, gps_lng, gps_accuracy, gps_text, notes, photo_paths,
            visited_at, synced_at, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            visit_uid,
            username,
            client_name.strip(),
            plot_no.strip(),
            bank_name.strip(),
            branch.strip(),
            gps_lat,
            gps_lng,
            gps_accuracy,
            gps_text or "",
            notes or "",
            json.dumps(photo_paths),
            visited_at or now,
            now,
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM site_visits WHERE visit_uid = ?", (visit_uid,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def list_site_visits(limit: int = 100, plot_no: str = None, client_name: str = None):
    import json
    conn = get_db()
    q = "SELECT * FROM site_visits WHERE 1=1"
    params = []
    if plot_no:
        q += " AND plot_no LIKE ?"
        params.append(f"%{plot_no}%")
    if client_name:
        q += " AND client_name LIKE ?"
        params.append(f"%{client_name}%")
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    for r in rows:
        try:
            r["photo_paths"] = json.loads(r.get("photo_paths") or "[]")
        except Exception:
            r["photo_paths"] = []
    return rows


def get_site_visit(visit_uid: str):
    import json
    conn = get_db()
    row = conn.execute("SELECT * FROM site_visits WHERE visit_uid = ?", (visit_uid,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["photo_paths"] = json.loads(d.get("photo_paths") or "[]")
    except Exception:
        d["photo_paths"] = []
    return d


def find_site_visits_for_plots(plot_nos: list, client_name: str = None):
    """Return latest site visit per plot_no (optional client filter)."""
    import json
    if not plot_nos:
        return []
    conn = get_db()
    results = []
    for pn in plot_nos:
        q = "SELECT * FROM site_visits WHERE plot_no = ?"
        params = [pn]
        if client_name:
            q += " AND client_name LIKE ?"
            params.append(f"%{client_name}%")
        q += " ORDER BY id DESC LIMIT 1"
        row = conn.execute(q, params).fetchone()
        if row:
            d = dict(row)
            try:
                d["photo_paths"] = json.loads(d.get("photo_paths") or "[]")
            except Exception:
                d["photo_paths"] = []
            results.append(d)
    conn.close()
    return results


def mark_site_visit_used(visit_uid: str, report_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE site_visits SET used_in_report_id = ? WHERE visit_uid = ?",
        (report_id, visit_uid),
    )
    conn.commit()
    conn.close()


def save_pdf_record(
    report_id: str,
    username: str,
    client_name: str,
    plot_nos: str,
    bank_name: str,
    branch: str,
    total_fmv: float,
    total_distress: float,
    valuation_date: str,
    pdf_path: str,
    site_visit_ids: list,
):
    import json
    ensure_storage_dirs()
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO pdf_records
           (report_id, created_by, client_name, plot_nos, bank_name, branch,
            total_fmv, total_distress, valuation_date, pdf_path, site_visit_ids, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            report_id,
            username,
            client_name,
            plot_nos,
            bank_name,
            branch,
            total_fmv,
            total_distress,
            valuation_date,
            pdf_path,
            json.dumps(site_visit_ids or []),
            datetime.utcnow().isoformat() + "Z",
        ),
    )
    conn.commit()
    conn.close()


def list_pdf_records(limit: int = 100):
    import json
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM pdf_records ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()]
    conn.close()
    for r in rows:
        try:
            r["site_visit_ids"] = json.loads(r.get("site_visit_ids") or "[]")
        except Exception:
            r["site_visit_ids"] = []
    return rows


def get_pdf_record(report_id: str):
    import json
    conn = get_db()
    row = conn.execute("SELECT * FROM pdf_records WHERE report_id = ?", (report_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["site_visit_ids"] = json.loads(d.get("site_visit_ids") or "[]")
    except Exception:
        d["site_visit_ids"] = []
    return d


# ---------- Banks & branches (editable from frontend) ----------

def ensure_banks_tables():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            mrv_pct REAL NOT NULL DEFAULT 0.70,
            grv_pct REAL NOT NULL DEFAULT 0.30,
            distress_factor REAL NOT NULL DEFAULT 0.80,
            notes TEXT DEFAULT '',
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL,
            branch_name TEXT NOT NULL,
            created_at TEXT,
            UNIQUE(bank_name, branch_name)
        )
    """)
    conn.commit()
    # Seed defaults if empty
    row = conn.execute("SELECT COUNT(*) AS c FROM banks").fetchone()
    if row and row["c"] == 0:
        defaults = [
            ("Nabil Bank Limited", 0.70, 0.30, 0.80),
            ("Laxmi Sunrise Bank Limited", 0.70, 0.30, 0.80),
            ("Machhapuchhre Bank Limited", 0.70, 0.30, 0.80),
            ("Global IME Bank Limited", 0.60, 0.40, 0.80),
            ("NIC Asia Bank Limited", 0.70, 0.30, 0.75),
            ("Prabhu Bank Limited", 0.60, 0.40, 0.80),
            # Sahakari / cooperatives (NMC format) — added alongside banks
            ("Nepal Multipurpose Cooperative Society", 0.70, 0.30, 0.80),
            ("Adhunik Saving and Credit Co-oprative Society Ltd", 0.70, 0.30, 0.80),
            ("Custom / Other", 0.70, 0.30, 0.80),
        ]
        for name, m, g, d in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO banks (name, mrv_pct, grv_pct, distress_factor, created_at) VALUES (?,?,?,?,?)",
                (name, m, g, d, datetime.utcnow().isoformat() + "Z"),
            )
        conn.commit()
    conn.close()


def list_banks_db():
    ensure_banks_tables()
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, name, mrv_pct, grv_pct, distress_factor, notes FROM banks ORDER BY name"
    ).fetchall()]
    conn.close()
    return rows


def get_bank_db(name: str):
    ensure_banks_tables()
    conn = get_db()
    row = conn.execute("SELECT * FROM banks WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_bank(name: str, mrv_pct: float, grv_pct: float, distress_factor: float, notes: str = ""):
    ensure_banks_tables()
    name = (name or "").strip()
    if not name:
        raise ValueError("Bank name is required")
    # normalize percents: accept 70 or 0.70
    if mrv_pct > 1.5:
        mrv_pct = mrv_pct / 100.0
    if grv_pct > 1.5:
        grv_pct = grv_pct / 100.0
    if distress_factor > 1.5:
        distress_factor = distress_factor / 100.0
    conn = get_db()
    existing = conn.execute("SELECT id FROM banks WHERE name = ?", (name,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE banks SET mrv_pct=?, grv_pct=?, distress_factor=?, notes=? WHERE name=?",
            (mrv_pct, grv_pct, distress_factor, notes or "", name),
        )
    else:
        conn.execute(
            "INSERT INTO banks (name, mrv_pct, grv_pct, distress_factor, notes, created_at) VALUES (?,?,?,?,?,?)",
            (name, mrv_pct, grv_pct, distress_factor, notes or "", datetime.utcnow().isoformat() + "Z"),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM banks WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row)


def delete_bank(name: str):
    ensure_banks_tables()
    conn = get_db()
    conn.execute("DELETE FROM banks WHERE name = ?", (name,))
    conn.execute("DELETE FROM branches WHERE bank_name = ?", (name,))
    conn.commit()
    conn.close()


def list_branches(bank_name: str = None):
    ensure_banks_tables()
    conn = get_db()
    if bank_name:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, bank_name, branch_name FROM branches WHERE bank_name = ? ORDER BY branch_name",
            (bank_name,),
        ).fetchall()]
    else:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, bank_name, branch_name FROM branches ORDER BY bank_name, branch_name"
        ).fetchall()]
    conn.close()
    return rows


def add_branch(bank_name: str, branch_name: str):
    ensure_banks_tables()
    bank_name = (bank_name or "").strip()
    branch_name = (branch_name or "").strip()
    if not bank_name or not branch_name:
        raise ValueError("Bank and branch name are required")
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO branches (bank_name, branch_name, created_at) VALUES (?,?,?)",
        (bank_name, branch_name, datetime.utcnow().isoformat() + "Z"),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, bank_name, branch_name FROM branches WHERE bank_name=? AND branch_name=?",
        (bank_name, branch_name),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def delete_branch(branch_id: int):
    ensure_banks_tables()
    conn = get_db()
    conn.execute("DELETE FROM branches WHERE id = ?", (branch_id,))
    conn.commit()
    conn.close()


def ensure_cooperative_presets():
    """Add Sahakari presets without removing existing banks."""
    ensure_banks_tables()
    conn = get_db()
    extra = [
        ("Nepal Multipurpose Cooperative Society", 0.70, 0.30, 0.80),
        ("Adhunik Saving and Credit Co-oprative Society Ltd", 0.70, 0.30, 0.80),
    ]
    from datetime import datetime
    for name, m, g, d in extra:
        conn.execute(
            "INSERT OR IGNORE INTO banks (name, mrv_pct, grv_pct, distress_factor, notes, created_at) VALUES (?,?,?,?,?,?)",
            (name, m, g, d, "Sahakari NMC format", datetime.utcnow().isoformat() + "Z"),
        )
    conn.commit()
    conn.close()
