import tomllib
import psycopg
from datetime import date


def get_connection():
    with open(".streamlit/secrets.toml", "rb") as f:
        s = tomllib.load(f)["postgres"]
    return psycopg.connect(
        host=s["host"], port=s["port"], dbname=s["dbname"],
        user=s["user"], password=s["password"]
    )


def alert_exists(cur, alert_type, alert_description):
    """Check if same alert already exists with OPEN status."""
    cur.execute("""
        SELECT alert_id FROM risk_alerts
        WHERE alert_type = %s
          AND alert_description = %s
          AND status = 'OPEN'
        LIMIT 1;
    """, (alert_type, alert_description))
    return cur.fetchone() is not None


def insert_alert(cur, alert_type, description, risk_level):
    """Insert alert only if not duplicate."""
    if alert_exists(cur, alert_type, description):
        return False
    cur.execute("""
        INSERT INTO risk_alerts
        (alert_type, alert_description, risk_level, detected_date, status)
        VALUES (%s, %s, %s, CURRENT_DATE, 'OPEN');
    """, (alert_type, description, risk_level))
    return True


# ---------- Risk 1: Low Inventory ----------
def check_low_inventory(cur):
    cur.execute("""
        SELECT m.material_name, i.quantity_on_hand, i.reorder_level
        FROM inventory i
        JOIN materials m ON i.material_id = m.material_id
        WHERE i.quantity_on_hand < i.reorder_level;
    """)
    count = 0
    for name, qty, reorder in cur.fetchall():
        desc = f"{name}: stock {qty} below reorder level {reorder}"
        if insert_alert(cur, "LOW_INVENTORY", desc, "HIGH"):
            count += 1
    return count


# ---------- Risk 2: Supplier Reliability ----------
def check_supplier_risk(cur):
    cur.execute("""
        SELECT s.supplier_name, sp.on_time_delivery_rate, sp.quality_score
        FROM supplier_performance sp
        JOIN suppliers s ON sp.supplier_id = s.supplier_id;
    """)
    count = 0
    for name, rate, quality in cur.fetchall():
        rate = float(rate) if rate else 0
        quality = float(quality) if quality else 0
        if rate < 70 or quality < 70:
            level = "HIGH"
        elif rate < 85 or quality < 85:
            level = "MEDIUM"
        else:
            continue
        desc = f"{name}: on-time {rate}%, quality {quality}%"
        if insert_alert(cur, "SUPPLIER_RISK", desc, level):
            count += 1
    return count


# ---------- Risk 3: Production Shortfall ----------
def check_production_risk(cur):
    cur.execute("""
        SELECT m.material_name, p.planned_quantity, p.produced_quantity
        FROM production p
        JOIN materials m ON p.material_id = m.material_id;
    """)
    count = 0
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
        desc = f"{name}: completion {completion:.1f}% (produced {produced}/{planned})"
        if insert_alert(cur, "PRODUCTION_RISK", desc, level):
            count += 1
    return count


# ---------- Risk 4: Delivery Risk ----------
def check_delivery_risk(cur):
    cur.execute("""
        SELECT delivery_id, delivery_status
        FROM deliveries;
    """)
    count = 0
    for did, status in cur.fetchall():
        if status in ("Late", "Delayed"):
            level = "HIGH"
        elif status in ("Pending", "In Transit"):
            level = "MEDIUM"
        else:
            continue
        desc = f"Delivery #{did}: status {status}"
        if insert_alert(cur, "DELIVERY_RISK", desc, level):
            count += 1
    return count


# ---------- Risk 5: Cost Increase ----------
def check_cost_risk(cur):
    cur.execute("""
        SELECT m.material_name, c.cost_date, c.unit_cost,
               LAG(c.unit_cost) OVER (PARTITION BY c.material_id ORDER BY c.cost_date) AS prev_cost
        FROM costs c
        JOIN materials m ON c.material_id = m.material_id
        ORDER BY m.material_name, c.cost_date;
    """)
    count = 0
    for name, cdate, unit, prev in cur.fetchall():
        if prev is None:
            continue
        prev = float(prev)
        unit = float(unit)
        if prev == 0:
            continue
        change = ((unit - prev) / prev) * 100
        if change > 10:
            desc = f"{name}: cost rose {change:.1f}% ({prev} -> {unit})"
            if insert_alert(cur, "COST_INCREASE", desc, "MEDIUM"):
                count += 1
    return count


# ---------- Main ----------
def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            new_alerts = 0
            new_alerts += check_low_inventory(cur)
            new_alerts += check_supplier_risk(cur)
            new_alerts += check_production_risk(cur)
            new_alerts += check_delivery_risk(cur)
            new_alerts += check_cost_risk(cur)
        conn.commit()
        print(f"Risk engine complete. New alerts inserted: {new_alerts}")

        # Summary
        with conn.cursor() as cur:
            cur.execute("""
                SELECT risk_level, COUNT(*) FROM risk_alerts
                WHERE status = 'OPEN'
                GROUP BY risk_level;
            """)
            print("\n--- Open Alerts Summary ---")
            for level, cnt in cur.fetchall():
                print(f"{level}: {cnt}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()