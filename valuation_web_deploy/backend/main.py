"""
Property Valuation Web Engine
Secure • Login-protected • Exact Excel formulas • PDF output • History
"""

import os
import io
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from calculations import ValuationRequest, run_valuation, BANK_CONFIGS
from pdf_generator import generate_valuation_pdf
from auth import (
    init_db, authenticate_user, create_access_token,
    get_current_user, save_valuation, list_valuations,
    LoginRequest, Token
)

app = FastAPI(title="Property Valuation Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def home():
    path = os.path.join(FRONTEND, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


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
    return {
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


@app.get("/api/banks")
async def banks(user=Depends(get_current_user)):
    return list(BANK_CONFIGS.keys())


@app.post("/api/calculate")
async def calculate(req: ValuationRequest, user=Depends(get_current_user)):
    try:
        result = run_valuation(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/generate-pdf")
async def generate_pdf(req: ValuationRequest, user=Depends(get_current_user)):
    try:
        result = run_valuation(req)
        # save history
        save_valuation(user["username"], req.model_dump(), result)
        pdf_bytes = generate_valuation_pdf(result)
        filename = f"Valuation_{req.client.client_name.replace(' ', '_')}_{req.valuation_date}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/history")
async def history(user=Depends(get_current_user)):
    return list_valuations(100)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
