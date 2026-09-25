import pandas as pd
import psycopg
import streamlit as st


def _connect():
    params = {
        "host": st.secrets["postgres"]["host"],
        "port": st.secrets["postgres"]["port"],
        "dbname": st.secrets["postgres"]["dbname"],
        "user": st.secrets["postgres"]["user"],
        "password": st.secrets["postgres"]["password"],
    }
    if "sslmode" in st.secrets["postgres"]:
        params["sslmode"] = st.secrets["postgres"]["sslmode"]
    return psycopg.connect(**params)


def _find_sheet(xl, keywords):
    """Find a sheet by matching any keyword (case-insensitive)."""
    for name in xl.sheet_names:
        low = name.lower().replace("_", "").replace(" ", "")
        for kw in keywords:
            if kw.lower() in low:
                return name
    return None


def _to_float(v, default=None):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def _to_int(v, default=None):
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except (ValueError, TypeError):
        return default


def _clean(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    return s if s else None


def import_excel(uploaded_file):
    """
    Import data from an Excel file.
    Returns dict with counts per sheet and any errors.
    """
    xl = pd.ExcelFile(uploaded_file)
    result = {"suppliers": 0, "materials": 0, "inventory": 0,
              "performance": 0, "production": 0, "errors": []}

    conn = _connect()
    try:
        with conn.cursor() as cur:
            # ---------- 1. SUPPLIERS ----------
            sheet = _find_sheet(xl, ["supplier"])
            if sheet:
                df = xl.parse(sheet)
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                for _, row in df.iterrows():
                    try:
                        name = _clean(row.get("supplier_name") or row.get("name"))
                        if not name:
                            continue
                        cur.execute("""
                            INSERT INTO suppliers
                            (supplier_name, contact_email, contact_phone, country, supplier_status)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            name,
                            _clean(row.get("contact_email") or row.get("email")),
                            _clean(row.get("contact_phone") or row.get("phone")),
                            _clean(row.get("country")),
                            _clean(row.get("supplier_status") or row.get("status")) or "Active",
                        ))
                        result["suppliers"] += 1
                    except Exception as e:
                        result["errors"].append(f"Supplier row: {e}")
                conn.commit()

            # ---------- 2. MATERIALS ----------
            sheet = _find_sheet(xl, ["material"])
            if sheet:
                df = xl.parse(sheet)
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                for _, row in df.iterrows():
                    try:
                        name = _clean(row.get("material_name") or row.get("name"))
                        if not name:
                            continue
                        supplier_id = None
                        sname = _clean(row.get("supplier_name") or row.get("supplier"))
                        if sname:
                            cur.execute("SELECT supplier_id FROM suppliers WHERE supplier_name=%s LIMIT 1;", (sname,))
                            r = cur.fetchone()
                            if r:
                                supplier_id = r[0]
                        cur.execute("""
                            INSERT INTO materials
                            (material_name, category, unit, unit_cost, supplier_id)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            name,
                            _clean(row.get("category")),
                            _clean(row.get("unit")),
                            _to_float(row.get("unit_cost")),
                            supplier_id,
                        ))
                        result["materials"] += 1
                    except Exception as e:
                        result["errors"].append(f"Material row: {e}")
                conn.commit()

            # ---------- 3. INVENTORY ----------
            sheet = _find_sheet(xl, ["inventory", "stock"])
            if sheet:
                df = xl.parse(sheet)
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                for _, row in df.iterrows():
                    try:
                        mname = _clean(row.get("material_name") or row.get("material"))
                        if not mname:
                            continue
                        cur.execute("SELECT material_id FROM materials WHERE material_name=%s LIMIT 1;", (mname,))
                        r = cur.fetchone()
                        if not r:
                            result["errors"].append(f"Inventory: material '{mname}' not found")
                            continue
                        cur.execute("""
                            INSERT INTO inventory
                            (material_id, quantity_on_hand, reorder_level, last_updated)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        """, (
                            r[0],
                            _to_int(row.get("quantity_on_hand") or row.get("quantity"), 0),
                            _to_int(row.get("reorder_level") or row.get("reorder"), 0),
                        ))
                        result["inventory"] += 1
                    except Exception as e:
                        result["errors"].append(f"Inventory row: {e}")
                conn.commit()

            # ---------- 4. SUPPLIER PERFORMANCE ----------
            sheet = _find_sheet(xl, ["performance", "supplierperf"])
            if sheet:
                df = xl.parse(sheet)
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                for _, row in df.iterrows():
                    try:
                        sname = _clean(row.get("supplier_name") or row.get("supplier"))
                        if not sname:
                            continue
                        cur.execute("SELECT supplier_id FROM suppliers WHERE supplier_name=%s LIMIT 1;", (sname,))
                        r = cur.fetchone()
                        if not r:
                            result["errors"].append(f"Performance: supplier '{sname}' not found")
                            continue
                        rate = _to_float(row.get("on_time_delivery_rate") or row.get("on_time"))
                        quality = _to_float(row.get("quality_score") or row.get("quality"))
                        if rate is None or quality is None:
                            continue
                        if rate < 70 or quality < 70:
                            status = "HIGH"
                        elif rate < 85 or quality < 85:
                            status = "MEDIUM"
                        else:
                            status = "NORMAL"
                        cur.execute("""
                            INSERT INTO supplier_performance
                            (supplier_id, evaluation_date, on_time_delivery_rate,
                             quality_score, performance_status)
                            VALUES (%s, CURRENT_DATE, %s, %s, %s)
                        """, (r[0], rate, quality, status))
                        result["performance"] += 1
                    except Exception as e:
                        result["errors"].append(f"Performance row: {e}")
                conn.commit()

            # ---------- 5. PRODUCTION ----------
            sheet = _find_sheet(xl, ["production", "produce"])
            if sheet:
                df = xl.parse(sheet)
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                for _, row in df.iterrows():
                    try:
                        mname = _clean(row.get("material_name") or row.get("material"))
                        if not mname:
                            continue
                        cur.execute("SELECT material_id FROM materials WHERE material_name=%s LIMIT 1;", (mname,))
                        r = cur.fetchone()
                        if not r:
                            result["errors"].append(f"Production: material '{mname}' not found")
                            continue
                        planned = _to_int(row.get("planned_quantity") or row.get("planned"), 0)
                        produced = _to_int(row.get("produced_quantity") or row.get("produced"), 0)
                        if planned <= 0:
                            continue
                        cur.execute("""
                            INSERT INTO production
                            (material_id, planned_quantity, produced_quantity,
                             production_date, production_status)
                            VALUES (%s, %s, %s, CURRENT_DATE, %s)
                        """, (
                            r[0], planned, produced,
                            _clean(row.get("production_status") or row.get("status")) or "Completed",
                        ))
                        result["production"] += 1
                    except Exception as e:
                        result["errors"].append(f"Production row: {e}")
                conn.commit()

    finally:
        conn.close()

    return result


def build_template_excel():
    """Create a sample Excel template with correct sheet names and columns."""
    import io as _io
    output = _io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as w:
        pd.DataFrame({
            "supplier_name": ["Metro Industrial", "Alpha Supplier"],
            "contact_email": ["metro@example.com", "alpha@example.com"],
            "contact_phone": ["0300-1234567", "0300-7654321"],
            "country": ["Pakistan", "Pakistan"],
            "supplier_status": ["Active", "Active"],
        }).to_excel(w, sheet_name="Suppliers", index=False)

        pd.DataFrame({
            "material_name": ["Steel Sheet", "Copper Wire"],
            "category": ["Metal", "Metal"],
            "unit": ["kg", "kg"],
            "unit_cost": [250, 850],
            "supplier_name": ["Metro Industrial", "Alpha Supplier"],
        }).to_excel(w, sheet_name="Materials", index=False)

        pd.DataFrame({
            "material_name": ["Steel Sheet", "Copper Wire"],
            "quantity_on_hand": [80, 500],
            "reorder_level": [150, 300],
        }).to_excel(w, sheet_name="Inventory", index=False)

        pd.DataFrame({
            "supplier_name": ["Metro Industrial", "Alpha Supplier"],
            "on_time_delivery_rate": [55, 92],
            "quality_score": [60, 88],
        }).to_excel(w, sheet_name="SupplierPerformance", index=False)

        pd.DataFrame({
            "material_name": ["Steel Sheet"],
            "planned_quantity": [700],
            "produced_quantity": [450],
            "production_status": ["Completed"],
        }).to_excel(w, sheet_name="Production", index=False)

    return output.getvalue()