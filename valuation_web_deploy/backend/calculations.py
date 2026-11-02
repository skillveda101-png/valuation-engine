"""
Valuation engine – configurable bank rules, optional belting, multi-plot, building.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


SQM_PER_DHUR = 16.93
SQM_PER_KATTHA = 338.63
SQM_PER_BIGHA = 6772.6
LAND_DEV_THRESHOLD = 508.737
LAND_DEV_PCT = 0.15


class BankRule(BaseModel):
    """Per-bank FMV weighting and distress."""
    name: str
    mrv_pct: float = 0.70          # market share e.g. 0.70 or 0.60
    grv_pct: float = 0.30          # govt share
    distress_factor: float = 0.80
    belt2_market_factor: float = 0.66
    belt3_market_factor: float = 0.50
    notes: str = ""


# Presets – user can override mrv/grv from frontend
BANK_PRESETS: Dict[str, BankRule] = {
    # --- Banks (existing) ---
    "Nabil Bank Limited": BankRule(name="Nabil Bank Limited", mrv_pct=0.70, grv_pct=0.30, distress_factor=0.80),
    "Laxmi Sunrise Bank Limited": BankRule(name="Laxmi Sunrise Bank Limited", mrv_pct=0.70, grv_pct=0.30, distress_factor=0.80),
    "Machhapuchhre Bank Limited": BankRule(name="Machhapuchhre Bank Limited", mrv_pct=0.70, grv_pct=0.30, distress_factor=0.80),
    "Global IME Bank Limited": BankRule(name="Global IME Bank Limited", mrv_pct=0.60, grv_pct=0.40, distress_factor=0.80),
    "NIC Asia Bank Limited": BankRule(name="NIC Asia Bank Limited", mrv_pct=0.70, grv_pct=0.30, distress_factor=0.75),
    "Prabhu Bank Limited": BankRule(name="Prabhu Bank Limited", mrv_pct=0.60, grv_pct=0.40, distress_factor=0.80),
    # --- Cooperatives / Sahakari (NMC format) ---
    "Nepal Multipurpose Cooperative Society": BankRule(
        name="Nepal Multipurpose Cooperative Society",
        mrv_pct=0.70, grv_pct=0.30, distress_factor=0.80,
        belt2_market_factor=0.66, belt3_market_factor=0.50,
        notes="Sahakari NMC norms: 70% market + 30% govt; DV 80% FMV",
    ),
    "Adhunik Saving and Credit Co-oprative Society Ltd": BankRule(
        name="Adhunik Saving and Credit Co-oprative Society Ltd",
        mrv_pct=0.70, grv_pct=0.30, distress_factor=0.80,
        notes="Sahakari format",
    ),
    "Custom / Other": BankRule(name="Custom / Other", mrv_pct=0.70, grv_pct=0.30, distress_factor=0.80),
}

# Keep alias used by main.py
BANK_CONFIGS = BANK_PRESETS


class PlotInput(BaseModel):
    plot_no: str
    lalpurja_sqm: float = 0
    cadastral_sqm: float = 0
    site_measurement_sqm: float = 0
    deducted_row_sqm: float = 0
    use_belting: bool = False
    belt1_sqm: float = 0
    belt2_sqm: float = 0
    belt3_sqm: float = 0
    # Land development deduction (Sahakari NMC): fraction e.g. 0.15 = 15%
    land_dev_pct: float = 0.0
    apply_land_dev_per_belt: bool = True
    govt_rate: float = 0
    govt_rate_unit: str = "Kattha"
    market_rate: float = 0
    market_rate_unit: str = "Kattha"
    location_type: str = "Nagarpalika"   # Nagarpalika | Gaupalika
    road_width_ft: float = 0
    east: str = ""
    west: str = ""
    north: str = ""
    south: str = ""
    road_width: str = ""
    road_type: str = ""
    frontage: str = ""
    distance_to_market: str = ""
    nearest_landmark: str = ""
    shape: str = "Regular (Refer the location & site plan)"
    importance: str = "Residential"
    title_deed_type: str = "Normal Sale"
    ownership_type: str = "Single"
    land_type: str = "Residential"
    reg_no: str = ""
    reg_date: str = ""
    reg_office: str = "Malpot Karyalaya Jhapa"
    cooling_off: str = "Elapsed"
    location_as_per_deed: str = ""
    access_at_blueprint: str = "No"
    revenue_paid: str = "Attached, Yes"
    motorable: str = "Yes"
    road_expansion: str = "No"
    road_access_charkilla: str = "Yes"
    guthi: str = "No"
    high_tension: str = "NOT PASSING"
    near_river: str = "No"
    near_border: str = "No"
    irregular_shape: str = "No"
    high_inclination: str = "No"
    sukumbasi: str = "No"
    joint_owners: str = "No"
    original_charkilla: str = ""
    municipal_charkilla: str = ""
    original_blueprint: str = "Yes"
    comments: str = ""
    gps: str = ""


class BuildingInput(BaseModel):
    has_building: bool = False
    building_type: str = "Residential"
    storeys: int = 0
    built_up_area_sqm: float = 0.0
    built_up_area_sft: float = 0.0
    year_of_completion_bs: str = ""
    naksa_pass: str = "Yes"
    completion_certificate: str = "Yes"
    constructed_as_per_drawing: str = "Yes"
    anticipated_life_years: int = 40
    pillar_size: str = "300 MM X 300 MM"
    construction_type: str = "RCC"
    construction_cost_per_sft: float = 2800.0
    depreciation_pct: float = 0.0


class ClientInput(BaseModel):
    client_name: str
    client_address_citizenship: str = ""
    citizenship_no: str = ""
    citizenship_date: str = ""
    father_name: str = ""
    contact_no: str = ""
    owner_name: str = ""
    owner_address_citizenship: str = ""
    owner_address_charkilla: str = ""
    owner_address_dhanipurja: str = ""
    owner_citizenship_no: str = ""
    owner_citizenship_date: str = ""
    owner_father: str = ""
    owner_contact: str = ""
    relationship: str = "Self"
    is_company: bool = False


class ValuationRequest(BaseModel):
    bank_name: str = "Nabil Bank Limited"
    branch: str = "Kakarvitta"
    # bank | cooperative (Sahakari) — same engine, different presets/report labels
    institution_type: str = "bank"
    # Allow override of bank rule from UI
    mrv_pct: Optional[float] = None
    grv_pct: Optional[float] = None
    distress_factor: Optional[float] = None
    # Loan eligibility factor applied on distress (NMC often 80% of DV)
    loan_factor: Optional[float] = 0.80
    valuation_date: str = ""
    agreement_date: str = "2023-11-26"
    letter_no: str = ""
    letter_received_date: str = ""
    field_visit_date: str = ""
    gps: str = ""
    loan_type: str = "Education Loan Only"
    client: ClientInput
    plots: List[PlotInput]
    building: Optional[BuildingInput] = None
    valuator_name: str = "Er. Yogesh Bhattarai"
    valuator_nec: str = 'NEC No. 14163 civil "A"'
    firm_name: str = "DYNAMIC SOLUTION PVT. LTD."
    firm_address: str = "MECHINAGAR MUNICIPALITY - 7, ITABHATTA, JHAPA"
    firm_reg_no: str = "238082/077/078"
    firm_pan: str = "609759503"
    firm_email: str = "d.solution100@gmail.com"
    firm_phone: str = "9816969180, 9864254625"


def rate_to_per_sqm(rate: float, unit: str) -> float:
    u = (unit or "Kattha").lower().replace(" ", "").replace(".", "")
    if u in ("sqm", "m2"):
        return rate
    if u in ("kattha", "katha"):
        return rate / SQM_PER_KATTHA
    if u == "dhur":
        return rate / SQM_PER_DHUR
    if u == "bigha":
        return rate / SQM_PER_BIGHA
    return rate / SQM_PER_KATTHA


def sqm_to_bkd(sqm: float) -> str:
    if abs(sqm) < 0.001:
        return "0-0-0"
    b = int(sqm // SQM_PER_BIGHA)
    rem = sqm % SQM_PER_BIGHA
    k = int(rem // SQM_PER_KATTHA)
    d = round((rem % SQM_PER_KATTHA) / SQM_PER_DHUR, 2)
    return f"{b}-{k}-{d}"


def resolve_bank(req: ValuationRequest) -> BankRule:
    base = BANK_PRESETS.get(req.bank_name, BANK_PRESETS["Custom / Other"]).model_copy()
    if req.mrv_pct is not None:
        base.mrv_pct = float(req.mrv_pct)
    if req.grv_pct is not None:
        base.grv_pct = float(req.grv_pct)
    if req.distress_factor is not None:
        base.distress_factor = float(req.distress_factor)
    # normalize if user only set one
    s = base.mrv_pct + base.grv_pct
    if abs(s - 1.0) > 0.01 and s > 0:
        base.mrv_pct = base.mrv_pct / s
        base.grv_pct = base.grv_pct / s
    return base


def calculate_plot_value(plot: PlotInput, bank: BankRule) -> Dict[str, Any]:
    # Net area before belting: site measurement minus ROW (matches NMC Excel)
    considered = max(0.0, (plot.site_measurement_sqm or plot.lalpurja_sqm) - plot.deducted_row_sqm)

    # Land development %: explicit plot override, else auto if area > threshold
    ld_pct = float(plot.land_dev_pct or 0.0)
    if ld_pct > 1.5:  # user entered 15 meaning 15%
        ld_pct = ld_pct / 100.0
    if ld_pct <= 0 and considered > LAND_DEV_THRESHOLD:
        ld_pct = LAND_DEV_PCT
    apply_dev = ld_pct > 0
    net_after_dev = considered * (1 - ld_pct) if apply_dev else considered
    dev_deduction = considered - net_after_dev

    use_belt = bool(plot.use_belting)
    b1 = plot.belt1_sqm if use_belt else considered
    b2 = plot.belt2_sqm if use_belt else 0.0
    b3 = plot.belt3_sqm if use_belt else 0.0
    if use_belt and (b1 + b2 + b3) < 0.1:
        b1, b2, b3 = considered, 0.0, 0.0

    total_belt = b1 + b2 + b3
    if use_belt and total_belt > 0.1 and abs(total_belt - considered) > 1:
        scale = considered / total_belt
        b1, b2, b3 = b1 * scale, b2 * scale, b3 * scale

    # NMC: LD applied per belt when belting is on
    if apply_dev and (plot.apply_land_dev_per_belt or use_belt):
        factor = 1 - ld_pct
        n1, n2, n3 = b1 * factor, b2 * factor, b3 * factor
    elif apply_dev:
        factor = 1 - ld_pct
        n1, n2, n3 = b1 * factor, b2 * factor, b3 * factor
    else:
        n1, n2, n3 = b1, b2, b3

    market_sqm = rate_to_per_sqm(plot.market_rate, plot.market_rate_unit)
    govt_sqm = rate_to_per_sqm(plot.govt_rate, plot.govt_rate_unit)

    def weighted(mkt_factor: float) -> float:
        return (market_sqm * mkt_factor * bank.mrv_pct) + (govt_sqm * bank.grv_pct)

    if use_belt:
        rate1 = weighted(1.0)
        rate2 = weighted(bank.belt2_market_factor)
        rate3 = weighted(bank.belt3_market_factor)
        fmv1, fmv2, fmv3 = n1 * rate1, n2 * rate2, n3 * rate3
    else:
        rate1 = weighted(1.0)
        rate2 = rate3 = 0.0
        fmv1, fmv2, fmv3 = net_after_dev * rate1, 0.0, 0.0
        n1, n2, n3 = net_after_dev, 0.0, 0.0

    raw_fmv = fmv1 + fmv2 + fmv3
    fmv = int(raw_fmv // 1000 * 1000)
    distress = int(round(fmv * bank.distress_factor))
    raw_mv = net_after_dev * market_sqm
    mv = int(raw_mv // 1000 * 1000)

    return {
        "plot_no": plot.plot_no,
        "use_belting": use_belt,
        "lalpurja_sqm": plot.lalpurja_sqm,
        "cadastral_sqm": plot.cadastral_sqm,
        "site_sqm": plot.site_measurement_sqm,
        "deducted_sqm": plot.deducted_row_sqm,
        "considered_sqm": round(considered, 2),
        "dev_deduction_sqm": round(dev_deduction, 2),
        "net_sqm": round(net_after_dev, 2),
        "belt1_raw": round(b1, 2),
        "belt2_raw": round(b2, 2),
        "belt3_raw": round(b3, 2),
        "belt1_net": round(n1, 2),
        "belt2_net": round(n2, 2),
        "belt3_net": round(n3, 2),
        "market_per_sqm": round(market_sqm, 2),
        "govt_per_sqm": round(govt_sqm, 2),
        "rate1": round(rate1, 2),
        "rate2": round(rate2, 2),
        "rate3": round(rate3, 2),
        "fmv1": round(fmv1, 0),
        "fmv2": round(fmv2, 0),
        "fmv3": round(fmv3, 0),
        "raw_fmv": round(raw_fmv, 0),
        "fmv": fmv,
        "mv": mv,
        "distress": distress,
        "net_kattha": round(net_after_dev / SQM_PER_KATTHA, 3),
        "bkd": sqm_to_bkd(net_after_dev),
        "apply_land_dev": apply_dev,
        "land_dev_pct": ld_pct,
        "location_type": plot.location_type,
        "road_width_ft": plot.road_width_ft,
    }


def calculate_building_value(bldg: Optional[BuildingInput]) -> Dict[str, Any]:
    if not bldg or not bldg.has_building:
        return {"fmv": 0, "distress": 0, "details": None}
    sft = bldg.built_up_area_sft
    if sft <= 0 and bldg.built_up_area_sqm > 0:
        sft = bldg.built_up_area_sqm * 10.7639
    gross = sft * bldg.construction_cost_per_sft
    dep = gross * (bldg.depreciation_pct / 100.0)
    net = gross - dep
    fmv = int(net // 1000 * 1000)
    return {
        "fmv": fmv,
        "distress": int(round(fmv * 0.8)),
        "details": {
            "built_up_sqm": bldg.built_up_area_sqm,
            "built_up_sft": round(sft, 2),
            "cost_per_sft": bldg.construction_cost_per_sft,
            "gross": round(gross, 0),
            "depreciation": round(dep, 0),
            "net": round(net, 0),
            "storeys": bldg.storeys,
            "type": bldg.construction_type,
            "building_type": bldg.building_type,
            "year": bldg.year_of_completion_bs,
            "naksa_pass": bldg.naksa_pass,
            "completion_certificate": bldg.completion_certificate,
            "constructed_as_per_drawing": bldg.constructed_as_per_drawing,
            "anticipated_life_years": bldg.anticipated_life_years,
            "pillar_size": bldg.pillar_size,
        },
    }


def number_to_words(n: float) -> str:
    n = int(round(n))
    if n == 0:
        return "Zero Rupees and No Paisa"
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
             "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def _w(x):
        if x < 10:
            return units[x]
        if x < 20:
            return teens[x - 10]
        if x < 100:
            return tens[x // 10] + (" " + units[x % 10] if x % 10 else "")
        if x < 1000:
            return units[x // 100] + " Hundred" + (" " + _w(x % 100) if x % 100 else "")
        return str(x)

    crore, rem = divmod(n, 10000000)
    lakh, rem = divmod(rem, 100000)
    thousand, rem = divmod(rem, 1000)
    parts = []
    if crore:
        parts.append(_w(crore) + " Crore")
    if lakh:
        parts.append(_w(lakh) + " Lakh")
    if thousand:
        parts.append(_w(thousand) + " Thousand")
    if rem:
        parts.append(_w(rem))
    return " ".join(parts) + " Rupees and No Paisa"


def run_valuation(req: ValuationRequest) -> Dict[str, Any]:
    bank = resolve_bank(req)
    plot_results = [calculate_plot_value(p, bank) for p in req.plots]
    land_fmv = sum(p["fmv"] for p in plot_results)
    land_mv = sum(p["mv"] for p in plot_results)
    land_distress = sum(p["distress"] for p in plot_results)
    any_belting = any(p["use_belting"] for p in plot_results)

    bldg = calculate_building_value(req.building)
    total_fmv = land_fmv + bldg["fmv"]
    total_distress = land_distress + bldg["distress"]
    lf = req.loan_factor if req.loan_factor is not None else 0.80
    if lf > 1.5:
        lf = lf / 100.0
    loan_amount = int(round(total_distress * lf) // 1000 * 1000)

    return {
        "request": req.model_dump(),
        "bank": bank.model_dump(),
        "plots": plot_results,
        "building": bldg,
        "any_belting": any_belting,
        "summary": {
            "land_fmv": land_fmv,
            "land_mv": land_mv,
            "land_distress": land_distress,
            "building_fmv": bldg["fmv"],
            "building_distress": bldg["distress"],
            "total_fmv": total_fmv,
            "loan_amount": loan_amount,
            "loan_factor": lf,
            "total_distress": total_distress,
            "fmv_words": number_to_words(total_fmv),
            "distress_words": number_to_words(total_distress),
        },
    }
