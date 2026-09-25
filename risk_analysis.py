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


def _exists(cur, atype, adesc):
    cur.execute("""
        SELECT 1 FROM risk_alerts
        WHERE alert_type=%s AND alert_description=%s AND status='OPEN'
        LIMIT 1;
    """, (atype, adesc))
    return cur.fetchone() is not None


def _add(cur, atype, adesc, level):
    if _exists(cur, atype, adesc):
        return 0
    cur.execute("""
        INSERT INTO risk_alerts
        (alert_type, alert_description, risk_level, detected_date, status)
        VALUES (%s, %s, %s, CURRENT_DATE, 'OPEN');
    """, (atype, adesc, level))
    return 1


def run_risk_analysis():
    conn = _connect()
    new_count = 0
    try:
        with conn.cursor() as cur:
            # 1. Low Inventory
            cur.execute("""
                SELECT m.material_name, i.quantity_on_hand, i.reorder_level
                FROM inventory i
                JOIN materials m ON i.material_id = m.material_id
                WHERE i.quantity_on_hand < i.reorder_level;
            """)
            for name, qty, reorder in cur.fetchall():
                desc = f"{name}: stock {qty} below reorder level {reorder}"
                new_count += _add(cur, "LOW_INVENTORY", desc, "HIGH")

            # 2. Supplier Risk
            cur.execute("""
                SELECT s.supplier_name, sp.on_time_delivery_rate, sp.quality_score
                FROM supplier_performance sp
                JOIN suppliers s ON sp.supplier_id = s.supplier_id;
            """)
            for name, rate, quality in cur.fetchall():
                rate = float(rate) if rate is not None else 0.0
                quality = float(quality) if quality is not None else 0.0
                if rate < 70 or quality < 70:
                    level = "HIGH"
                elif rate < 85 or quality < 85:
                    level = "MEDIUM"
                else:
                    continue
                desc = f"{name}: on-time {rate}%, quality {quality}%"
                new_count += _add(cur, "SUPPLIER_RISK", desc, level)

            # 3. Production Risk
            cur.execute("""
                SELECT m.material_name, p.planned_quantity, p.produced_quantity
                FROM production p
                JOIN materials m ON p.material_id = m.material_id;
            """)
            for name, planned, produced in cur.fetchall():
                if not planned or planned == 0:
                    continue
                completion = (float(produced) / float(planned)) * 100
                if completion < 70:
                    level = "HIGH"
                elif completion < 85:
                    level = "MEDIUM"
                else:
                    continue
                desc = f"{name}: completion {completion:.1f}% ({produced}/{planned})"
                new_count += _add(cur, "PRODUCTION_RISK", desc, level)

            # 4. Delivery Risk
            cur.execute("SELECT delivery_id, delivery_status FROM deliveries;")
            for did, status in cur.fetchall():
                if status in ("Late", "Delayed"):
                    level = "HIGH"
                elif status in ("Pending", "In Transit"):
                    level = "MEDIUM"
                else:
                    continue
                desc = f"Delivery #{did}: status {status}"
                new_count += _add(cur, "DELIVERY_RISK", desc, level)

            # 5. Cost Increase
            cur.execute("""
                SELECT m.material_name, c.cost_date, c.unit_cost,
                       LAG(c.unit_cost) OVER (PARTITION BY c.material_id ORDER BY c.cost_date) AS prev
                FROM costs c
                JOIN materials m ON c.material_id = m.material_id
                ORDER BY m.material_name, c.cost_date;
            """)
            for name, cdate, unit, prev in cur.fetchall():
                if prev is None or prev == 0:
                    continue
                change = ((float(unit) - float(prev)) / float(prev)) * 100
                if change > 10:
                    desc = f"{name}: cost rose {change:.1f}% ({prev} -> {unit})"
                    new_count += _add(cur, "COST_INCREASE", desc, "MEDIUM")

        conn.commit()
    finally:
        conn.close()
    return new_count