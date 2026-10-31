"""
Property Valuation Web Engine – API + report verification
"""

import os
import hashlib
import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from calculations import ValuationRequest, run_valuation, BANK_PRESETS
from pdf_generator import generate_valuation_pdf
from auth import (
    init_db, authenticate_user, create_access_token,
    get_current_user, save_valuation, list_valuations,
    LoginRequest, Token,
    save_report_record, get_report_record, ensure_reports_table,
)

app = FastAPI(title="Property Valuation Engine", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
# Public base URL for verification QR (override with env on Render)
PUBLIC_BASE = os.environ.get("PUBLIC_API_URL", "https://valuation-engine-m013.onrender.com").rstrip("/")


@app.on_event("startup")
def startup():
    init_db()
    ensure_reports_table()


@app.get("/", response_class=HTMLResponse)
async def home():
    path = os.path.join(FRONTEND, "index.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Valuation API</h1>")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.1.0"}


@app.post("/api/login", response_model=Token)
async def login(body: LoginRequest):
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return Token(
        access_token=token,
        username=user["username"],
        full_name=user["full_name"] or user["username"],
        role=user["role"],
    )


@app.get("/api/me")
async def me(user=Depends(get_current_user)):
    return {"username": user["username"], "full_name": user["full_name"], "role": user["role"]}


@app.get("/api/banks")
async def banks():
    return [
        {"name": b.name, "mrv_pct": b.mrv_pct, "grv_pct": b.grv_pct, "distress_factor": b.distress_factor}
        for b in BANK_PRESETS.values()
    ]


@app.post("/api/calculate")
async def calculate(req: ValuationRequest, user=Depends(get_current_user)):
    try:
        return run_valuation(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _report_hash(req: dict, summary: dict) -> str:
    raw = f"{req.get('bank_name')}|{req.get('valuation_date')}|{summary.get('total_fmv')}|{summary.get('total_distress')}|"
    client = req.get("client") or {}
    raw += f"{client.get('client_name')}|{client.get('owner_name')}|"
    for p in req.get("plots") or []:
        raw += f"{p.get('plot_no')}:{p.get('site_measurement_sqm')}:"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@app.post("/api/pdf")
async def pdf(req: ValuationRequest, user=Depends(get_current_user)):
    try:
        result = run_valuation(req)
        report_id = uuid.uuid4().hex[:12].upper()
        content_hash = _report_hash(req.model_dump(), result["summary"])
        verify_url = f"{PUBLIC_BASE}/verify/{report_id}"

        result["report_id"] = report_id
        result["content_hash"] = content_hash
        result["verify_url"] = verify_url

        pdf_bytes = generate_valuation_pdf(result)

        try:
            save_report_record(report_id, user["username"], req.model_dump(), result["summary"], content_hash)
            save_valuation(user["username"], req.model_dump(), result["summary"])
        except Exception:
            pass

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=valuation_{report_id}.pdf",
                "X-Report-Id": report_id,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/history")
async def history(user=Depends(get_current_user)):
    return list_valuations(user["username"])


@app.get("/api/verify/{report_id}")
async def verify_api(report_id: str):
    rec = get_report_record(report_id.upper())
    if not rec:
        rec = get_report_record(report_id)
    if not rec:
        return JSONResponse(
            status_code=404,
            content={"valid": False, "message": "Report not found in Dynamic Solution registry. May be forged or deleted."},
        )
    return {
        "valid": True,
        "message": "Authentic report issued by Dynamic Solution Pvt. Ltd.",
        "report_id": rec["id"],
        "created_at": rec["created_at"],
        "client_name": rec["client_name"],
        "owner_name": rec["owner_name"],
        "bank_name": rec["bank_name"],
        "branch": rec["branch"],
        "plot_nos": rec["plot_nos"],
        "total_fmv": rec["total_fmv"],
        "total_distress": rec["total_distress"],
        "valuation_date": rec["valuation_date"],
        "content_hash": rec["content_hash"],
    }


@app.get("/verify/{report_id}", response_class=HTMLResponse)
async def verify_page(report_id: str):
    rec = get_report_record(report_id.upper()) or get_report_record(report_id)
    if not rec:
        return HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset=utf-8><title>Report verification</title>
            <style>body{{font-family:system-ui;max-width:560px;margin:40px auto;padding:20px}}
            .bad{{background:#fed7d7;border:1px solid #c53030;padding:16px;border-radius:8px}}</style></head>
            <body><h1>Dynamic Solution – Report Check</h1>
            <div class="bad"><b>Not found</b><br>Report ID <code>{report_id}</code> is not in our registry.
            This copy may be forged, altered, or never issued by us.</div>
            <p style="color:#666;font-size:14px">Only reports generated by Dynamic Solution Valuation Engine appear here.</p>
            </body></html>""",
            status_code=404,
        )
    return HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset=utf-8><title>Verified report {rec['id']}</title>
        <style>
        body{{font-family:system-ui;max-width:560px;margin:40px auto;padding:20px;background:#f7fafc}}
        .ok{{background:#c6f6d5;border:1px solid #276749;padding:16px;border-radius:8px}}
        table{{width:100%;border-collapse:collapse;margin-top:12px;background:#fff}}
        td{{border:1px solid #e2e8f0;padding:8px;font-size:14px}}
        td:first-child{{font-weight:600;width:40%;background:#edf2f7}}
        h1{{color:#1a365d;font-size:1.25rem}}
        </style></head><body>
        <h1>Dynamic Solution Pvt. Ltd.</h1>
        <div class="ok"><b>✓ Authentic report</b><br>This valuation was issued by our system and is registered.</div>
        <table>
          <tr><td>Report ID</td><td>{rec['id']}</td></tr>
          <tr><td>Issued at (UTC)</td><td>{rec['created_at']}</td></tr>
          <tr><td>Valuation date</td><td>{rec['valuation_date']}</td></tr>
          <tr><td>Client</td><td>{rec['client_name']}</td></tr>
          <tr><td>Owner</td><td>{rec['owner_name']}</td></tr>
          <tr><td>Bank / Branch</td><td>{rec['bank_name']} / {rec['branch']}</td></tr>
          <tr><td>Plot No(s)</td><td>{rec['plot_nos']}</td></tr>
          <tr><td>Total FMV (NRs)</td><td>{rec['total_fmv']:,.0f}</td></tr>
          <tr><td>Distress value (NRs)</td><td>{rec['total_distress']:,.0f}</td></tr>
          <tr><td>Content fingerprint</td><td style="font-size:11px;word-break:break-all">{rec['content_hash']}</td></tr>
        </table>
        <p style="font-size:13px;color:#718096;margin-top:16px">
        If FMV/DV on a paper copy differ from the values above, the paper may have been altered.
        Always cross-check this page. QR on the PDF opens this verification.
        </p>
        </body></html>"""
    )
