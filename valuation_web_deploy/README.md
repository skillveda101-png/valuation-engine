# Property Valuation Web Engine v2

**Your Excel valuation templates → Secure web app → Professional PDF**

Employees fill a form. The calculation engine stays on **your server**.  
They can never download or share the formulas.

---

## Exact formula (matches your Excel)

For each belt:
1. Net area = Belt area × 85% (15% standard deduction)
2. Convert to Kattha (÷ 338.63)
3. Weighted rate:
   - Belt 1: 70% × Market + 30% × Government
   - Belt 2: 70% × (Market × 0.66) + 30% × Government
   - Belt 3: 70% × (Market × 0.50) + 30% × Government
4. FMV = ROUNDDOWN(sum of belt values, nearest 1000)
5. Distress Value = FMV × 0.80

Verified against your sample (Plot 4689):  
**Excel FMV 8,647,000 = Engine FMV 8,647,000** ✓

---

## Quick Start

```bash
cd valuation_web
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: **http://localhost:8000**

**Login:** `admin` / `admin123`  
(Change this immediately after first use!)

---

## Features

| Feature | Status |
|---------|--------|
| Exact Excel belting formula | ✅ Verified |
| Login + JWT authentication | ✅ |
| Multiple plots | ✅ |
| Existing building | ✅ |
| Professional multi-page PDF | ✅ |
| Valuation history (SQLite) | ✅ |
| Bank-specific rates | ✅ |
| Unit conversion (Kattha/Dhur/sq.m) | ✅ |

---

## Project structure

```
valuation_web/
├── backend/
│   ├── main.py              FastAPI routes
│   ├── calculations.py      ALL formulas (keep private)
│   ├── pdf_generator.py     ReportLab PDF
│   └── auth.py              Login + history DB
├── frontend/
│   └── index.html           Form + login UI
├── data/                    SQLite database (auto-created)
├── requirements.txt
└── README.md
```

---

## Security notes

- Calculation logic never leaves the server
- Employees only see the form and the generated PDF
- Change the default admin password
- For production: put behind HTTPS (nginx + Let's Encrypt)
- Set environment variable `VALUATION_SECRET` for JWT key

---

## Next improvements you can ask for

- Add more users from the UI
- Upload site photographs into the PDF
- Company logo on every page
- Export history to Excel
- Role-based access (valuator vs admin)
