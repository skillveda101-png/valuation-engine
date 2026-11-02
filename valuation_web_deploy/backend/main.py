"""
Property Valuation Web Engine – API + field app + report verification
"""

import os
import hashlib
import uuid
import base64
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from calculations import ValuationRequest, run_valuation, BANK_PRESETS
from pdf_generator import generate_valuation_pdf
from auth import (
    init_db, authenticate_user, create_access_token,
    get_current_user, save_valuation, list_valuations,
    LoginRequest, Token,
    save_report_record, get_report_record, ensure_reports_table,
    save_site_visit, list_site_visits, get_site_visit,
    find_site_visits_for_plots, mark_site_visit_used,
    save_pdf_record, list_pdf_records, get_pdf_record,
    ensure_storage_dirs, PHOTOS_DIR, PDFS_DIR,
    ensure_banks_tables, list_banks_db, upsert_bank, delete_bank,
    ensure_cooperative_presets,
    list_branches, add_branch, delete_branch, get_bank_db,
)

app = FastAPI(title="Property Valuation Engine", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")  # bundled with backend for Render
PUBLIC_BASE = os.environ.get("PUBLIC_API_URL", "https://valuation-engine-m013.onrender.com").rstrip("/")


@app.on_event("startup")
def startup():
    init_db()
    ensure_reports_table()
    ensure_storage_dirs()
    ensure_banks_tables()
    try:
        ensure_cooperative_presets()
    except Exception:
        pass


@app.get("/", response_class=HTMLResponse)
async def home():
    path = os.path.join(FRONTEND, "index.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Valuation API</h1>")


@app.get("/field", response_class=HTMLResponse)
async def field_app():
    """Mobile field-visit app (installable PWA)."""
    path = os.path.join(FRONTEND, "field.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Field app not found</h1>", status_code=404)


@app.get("/manifest.json")
async def manifest():
    path = os.path.join(FRONTEND, "manifest.json")
    if os.path.isfile(path):
        return FileResponse(path, media_type="application/manifest+json")
    raise HTTPException(404)


@app.get("/sw.js")
async def service_worker():
    path = os.path.join(FRONTEND, "sw.js")
    if os.path.isfile(path):
        return FileResponse(path, media_type="application/javascript")
    raise HTTPException(404)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}


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
    rows = list_banks_db()
    if rows:
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "mrv_pct": r["mrv_pct"],
                "grv_pct": r["grv_pct"],
                "distress_factor": r["distress_factor"],
                "notes": r.get("notes") or "",
            }
            for r in rows
        ]
    # fallback to code presets
    return [
        {"name": b.name, "mrv_pct": b.mrv_pct, "grv_pct": b.grv_pct, "distress_factor": b.distress_factor}
        for b in BANK_PRESETS.values()
    ]


class BankBody(BaseModel):
    name: str
    mrv_pct: float = 70  # accept 70 or 0.70
    grv_pct: float = 30
    distress_factor: float = 80
    notes: str = ""


@app.post("/api/banks")
async def create_or_update_bank(body: BankBody, user=Depends(get_current_user)):
    try:
        rec = upsert_bank(body.name, body.mrv_pct, body.grv_pct, body.distress_factor, body.notes)
        return {"ok": True, "bank": rec}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/banks/{name}")
async def api_delete_bank(name: str, user=Depends(get_current_user)):
    delete_bank(name)
    return {"ok": True}


@app.get("/api/branches")
async def api_list_branches(bank_name: Optional[str] = None, user=Depends(get_current_user)):
    return list_branches(bank_name)


class BranchBody(BaseModel):
    bank_name: str
    branch_name: str


@app.post("/api/branches")
async def api_add_branch(body: BranchBody, user=Depends(get_current_user)):
    try:
        rec = add_branch(body.bank_name, body.branch_name)
        return {"ok": True, "branch": rec}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/branches/{branch_id}")
async def api_delete_branch(branch_id: int, user=Depends(get_current_user)):
    delete_branch(branch_id)
    return {"ok": True}


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


class PdfRequest(ValuationRequest):
    """ValuationRequest + optional site photo paths / visit ids."""
    site_photo_paths: Optional[List[str]] = None
    site_visit_uids: Optional[List[str]] = None


@app.post("/api/pdf")
async def pdf(req: PdfRequest, user=Depends(get_current_user)):
    try:
        result = run_valuation(req)
        report_id = uuid.uuid4().hex[:12].upper()
        content_hash = _report_hash(req.model_dump(), result["summary"])
        verify_url = f"{PUBLIC_BASE}/verify/{report_id}"

        result["report_id"] = report_id
        result["content_hash"] = content_hash
        result["verify_url"] = verify_url

        # Resolve photos from site visits if not explicitly provided
        photo_paths = list(req.site_photo_paths or [])
        visit_uids = list(req.site_visit_uids or [])
        plot_nos = [p.plot_no for p in req.plots if p.plot_no]
        visits = find_site_visits_for_plots(
            plot_nos, req.client.client_name if req.client else None
        )
        if not photo_paths:
            for v in visits:
                photo_paths.extend(v.get("photo_paths") or [])
                if v.get("visit_uid") and v["visit_uid"] not in visit_uids:
                    visit_uids.append(v["visit_uid"])
        result["site_photo_paths"] = photo_paths
        # Ensure request dict has gps if visits have it
        req_dict = req.model_dump()
        if not req_dict.get("gps") and visits:
            for v in visits:
                if v.get("gps_text"):
                    req_dict["gps"] = v["gps_text"]
                    break
                if v.get("gps_lat") is not None and v.get("gps_lng") is not None:
                    req_dict["gps"] = f"{v['gps_lat']:.6f}, {v['gps_lng']:.6f}"
                    break
        result["request"] = req_dict

        pdf_bytes = generate_valuation_pdf(result)

        # Persist PDF to disk for record keeping
        ensure_storage_dirs()
        pdf_filename = f"valuation_{report_id}.pdf"
        pdf_path = os.path.join(PDFS_DIR, pdf_filename)
        try:
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception:
            pdf_path = ""

        try:
            save_report_record(report_id, user["username"], req_dict, result["summary"], content_hash)
            save_valuation(user["username"], req_dict, result["summary"])
            client_name = (req.client.client_name if req.client else "") or ""
            plot_nos_str = ", ".join(p.plot_no for p in req.plots)
            save_pdf_record(
                report_id, user["username"], client_name, plot_nos_str,
                req.bank_name, req.branch,
                result["summary"].get("total_fmv", 0),
                result["summary"].get("total_distress", 0),
                req.valuation_date, pdf_path, visit_uids,
            )
            for uid in visit_uids:
                try:
                    mark_site_visit_used(uid, report_id)
                except Exception:
                    pass
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
    return list_valuations(50)


# ---------- Site visits (field app) ----------

class SiteVisitPayload(BaseModel):
    visit_uid: str
    client_name: str
    plot_no: str
    bank_name: str
    branch: str
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_accuracy: Optional[float] = None
    gps_text: str = ""
    notes: str = ""
    visited_at: str = ""
    # photos as base64 list: data:image/jpeg;base64,... or raw base64
    photos_b64: Optional[List[str]] = None


@app.post("/api/site-visits")
async def create_site_visit(body: SiteVisitPayload, user=Depends(get_current_user)):
    if not body.client_name or not body.plot_no or not body.bank_name or not body.branch:
        raise HTTPException(400, "client_name, plot_no, bank_name, branch are required")
    if not body.photos_b64 or len(body.photos_b64) == 0:
        raise HTTPException(400, "At least one photo is required")

    ensure_storage_dirs()
    photo_paths = []
    for i, b64 in enumerate(body.photos_b64[:8]):  # max 8 photos
        try:
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            raw = base64.b64decode(b64)
            fname = f"{body.visit_uid}_{i}.jpg"
            fpath = os.path.join(PHOTOS_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(raw)
            photo_paths.append(fname)
        except Exception as e:
            raise HTTPException(400, f"Invalid photo data: {e}")

    gps_text = body.gps_text
    if not gps_text and body.gps_lat is not None and body.gps_lng is not None:
        gps_text = f"{body.gps_lat:.6f}, {body.gps_lng:.6f}"

    rec = save_site_visit(
        visit_uid=body.visit_uid or uuid.uuid4().hex,
        username=user["username"],
        client_name=body.client_name,
        plot_no=body.plot_no,
        bank_name=body.bank_name,
        branch=body.branch,
        gps_lat=body.gps_lat,
        gps_lng=body.gps_lng,
        gps_accuracy=body.gps_accuracy,
        gps_text=gps_text,
        notes=body.notes or "",
        photo_paths=photo_paths,
        visited_at=body.visited_at or "",
    )
    return {"ok": True, "visit": rec}


@app.get("/api/site-visits")
async def api_list_site_visits(
    plot_no: Optional[str] = None,
    client_name: Optional[str] = None,
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    return list_site_visits(limit=limit, plot_no=plot_no, client_name=client_name)


@app.get("/api/site-visits/{visit_uid}")
async def api_get_site_visit(visit_uid: str, user=Depends(get_current_user)):
    rec = get_site_visit(visit_uid)
    if not rec:
        raise HTTPException(404, "Site visit not found")
    return rec


@app.get("/api/site-visits/for-plots")
async def api_site_visits_for_plots(
    plot_nos: str = Query(..., description="Comma-separated plot numbers"),
    client_name: Optional[str] = None,
    user=Depends(get_current_user),
):
    nos = [p.strip() for p in plot_nos.split(",") if p.strip()]
    return find_site_visits_for_plots(nos, client_name)


@app.get("/api/photos/{filename}")
async def get_photo(filename: str):
    """Serve stored site photos (auth not required for PDF embedding convenience; filenames are UUIDs)."""
    # Prevent path traversal
    safe = os.path.basename(filename)
    path = os.path.join(PHOTOS_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(404, "Photo not found")
    return FileResponse(path, media_type="image/jpeg")


# ---------- PDF / report records ----------

@app.get("/api/pdf-records")
async def api_list_pdf_records(user=Depends(get_current_user)):
    return list_pdf_records(100)


@app.get("/api/pdf-records/{report_id}/download")
async def download_stored_pdf(report_id: str, user=Depends(get_current_user)):
    rec = get_pdf_record(report_id)
    if not rec or not rec.get("pdf_path") or not os.path.isfile(rec["pdf_path"]):
        raise HTTPException(404, "Stored PDF not found")
    return FileResponse(
        rec["pdf_path"],
        media_type="application/pdf",
        filename=f"valuation_{report_id}.pdf",
    )


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
