import sys, os, io
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import psycopg
import pandas as pd
from fpdf import FPDF
from auth import login_page, logout_button
from risk_analysis import run_risk_analysis
from excel_import import import_excel, build_template_excel
from data_entry import (
    supplier_form,
    material_form,
    inventory_form,
    supplier_performance_form,
    production_form,
    order_form,
    delivery_form
)

st.set_page_config(
    page_title="Industrial Decision Intelligence",
    page_icon="🏭",
    layout="wide"
)

if "user" not in st.session_state:
    login_page()
    st.stop()

logout_button()

st.title("🏭 Industrial Decision Intelligence & Risk Management System")
st.caption("Industrial monitoring, analysis and risk management dashboard")

def get_connection():
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

def run_query(query):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()

def update_alert_status(alert_id, new_status):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE risk_alerts SET status = %s WHERE alert_id = %s;",
                (new_status, alert_id)
            )
        conn.commit()
    finally:
        conn.close()

def df_to_excel_bytes(sheets):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df_copy = df.copy()
            for col in df_copy.columns:
                if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                    try:
                        df_copy[col] = df_copy[col].dt.tz_localize(None)
                    except (TypeError, AttributeError):
                        pass
            df_copy.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()

def build_summary_pdf(
    suppliers_count, materials_count, open_alerts, high, medium,
    df_inv, df_sup, df_prod, df_dlv
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Industrial Decision Intelligence", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Executive Risk Summary Report", ln=True, align="C")
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "1. Key Metrics", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Total Suppliers: {suppliers_count}", ln=True)
    pdf.cell(0, 6, f"Total Materials: {materials_count}", ln=True)
    pdf.cell(0, 6, f"Open Alerts: {open_alerts}", ln=True)
    pdf.cell(0, 6, f"HIGH risk alerts: {high}", ln=True)
    pdf.cell(0, 6, f"MEDIUM risk alerts: {medium}", ln=True)
    pdf.ln(4)

    def add_section(title, df):
        if df.empty:
            return
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 9)
        headers = list(df.columns)
        col_width = 190 / max(len(headers), 1)
        for h in headers:
            pdf.cell(col_width, 6, str(h)[:20], border=1)
        pdf.ln()
        for _, row in df.head(15).iterrows():
            for h in headers:
                pdf.cell(col_width, 6, str(row[h])[:20], border=1)
            pdf.ln()
        pdf.ln(3)

    add_section("2. Low Stock Inventory", df_inv)
    add_section("3. Supplier Performance", df_sup)
    add_section("4. Production Performance", df_prod)
    add_section("5. Deliveries", df_dlv)

    return bytes(pdf.output())

# ---------- Load Data ----------
try:
    suppliers_count = run_query("SELECT COUNT(*) AS c FROM suppliers;")["c"][0]
    materials_count = run_query("SELECT COUNT(*) AS c FROM materials;")["c"][0]
    alerts_count    = run_query("SELECT COUNT(*) AS c FROM risk_alerts WHERE status='OPEN';")["c"][0]
    high_count      = run_query("SELECT COUNT(*) AS c FROM risk_alerts WHERE risk_level='HIGH' AND status='OPEN';")["c"][0]
    medium_count    = run_query("SELECT COUNT(*) AS c FROM risk_alerts WHERE risk_level='MEDIUM' AND status='OPEN';")["c"][0]
    normal_count    = run_query("SELECT COUNT(*) AS c FROM risk_alerts WHERE risk_level='NORMAL' AND status='OPEN';")["c"][0]

    df_inventory_all = run_query("""
        SELECT m.material_name,
               i.quantity_on_hand,
               i.reorder_level,
               (i.reorder_level - i.quantity_on_hand) AS shortage,
               CASE WHEN i.quantity_on_hand < i.reorder_level THEN 'LOW' ELSE 'OK' END AS status
        FROM inventory i
        JOIN materials m ON i.material_id = m.material_id
        ORDER BY shortage DESC;
    """)

    df_suppliers_all = run_query("""
        SELECT s.supplier_name,
               sp.on_time_delivery_rate,
               sp.quality_score,
               sp.performance_status,
               CASE
                   WHEN sp.on_time_delivery_rate < 70 OR sp.quality_score < 70 THEN 'HIGH'
                   WHEN sp.on_time_delivery_rate < 85 OR sp.quality_score < 85 THEN 'MEDIUM'
                   ELSE 'NORMAL'
               END AS risk_level
        FROM supplier_performance sp
        JOIN suppliers s ON sp.supplier_id = s.supplier_id
        ORDER BY risk_level, s.supplier_name;
    """)

    df_production_all = run_query("""
        SELECT m.material_name,
               p.planned_quantity,
               p.produced_quantity,
               ROUND((p.produced_quantity::numeric / p.planned_quantity) * 100, 2) AS completion_percent,
               p.production_status,
               CASE
                   WHEN (p.produced_quantity::numeric / p.planned_quantity) * 100 < 70 THEN 'HIGH'
                   WHEN (p.produced_quantity::numeric / p.planned_quantity) * 100 < 85 THEN 'MEDIUM'
                   ELSE 'NORMAL'
               END AS risk_level
        FROM production p
        JOIN materials m ON p.material_id = m.material_id
        ORDER BY risk_level, completion_percent;
    """)

    df_deliveries_all = run_query("""
        SELECT d.delivery_id, d.order_id, d.delivery_date,
               d.expected_date, d.delivery_status, d.delivery_cost
        FROM deliveries d
        ORDER BY d.delivery_id DESC;
    """)

    df_costs_all = run_query("""
        SELECT m.material_name, c.cost_date, c.unit_cost,
               c.total_cost, c.cost_type
        FROM costs c
        JOIN materials m ON c.material_id = m.material_id
        ORDER BY m.material_name, c.cost_date;
    """)

except Exception as e:
    st.error("Database error:")
    st.write(e)
    st.stop()

# ---------- Executive Overview ----------
st.subheader("Executive Overview")
c1, c2, c3 = st.columns(3)
c1.metric("Suppliers", suppliers_count)
c2.metric("Materials", materials_count)
c3.metric("Open Alerts", alerts_count)

c4, c5, c6 = st.columns(3)
c4.metric("🔴 HIGH Risk", high_count)
c5.metric("🟡 MEDIUM Risk", medium_count)
c6.metric("🟢 NORMAL", normal_count)

st.markdown("---")

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📦 Inventory",
    "🏭 Suppliers",
    "⚙️ Production",
    "🚚 Deliveries",
    "💰 Costs",
    "🚨 Risk Alerts",
    "📝 Data Entry",
    "📄 Reports"
])

# ================= INVENTORY =================
with tab1:
    st.subheader("Inventory Status")

    col1, col2 = st.columns([2, 1])
    with col1:
        search_inv = st.text_input("🔍 Search material name", key="inv_search")
    with col2:
        status_inv = st.selectbox("Status", ["All", "LOW", "OK"], key="inv_status")

    df_inv = df_inventory_all.copy()
    if search_inv:
        df_inv = df_inv[df_inv["material_name"].str.contains(search_inv, case=False, na=False)]
    if status_inv != "All":
        df_inv = df_inv[df_inv["status"] == status_inv]

    if df_inv.empty:
        st.info("No matching records.")
    else:
        st.write(f"**{len(df_inv)} record(s)**")
        st.dataframe(df_inv, use_container_width=True)
        low = df_inv[df_inv["status"] == "LOW"]
        if not low.empty:
            st.warning(f"⚠️ {len(low)} material(s) are below reorder level.")

# ================= SUPPLIERS =================
with tab2:
    st.subheader("Supplier Performance Analysis")

    col1, col2 = st.columns([2, 1])
    with col1:
        search_sup = st.text_input("🔍 Search supplier name", key="sup_search")
    with col2:
        risk_sup = st.selectbox("Risk Level", ["All", "HIGH", "MEDIUM", "NORMAL"], key="sup_risk")

    df_sup = df_suppliers_all.copy()
    if search_sup:
        df_sup = df_sup[df_sup["supplier_name"].str.contains(search_sup, case=False, na=False)]
    if risk_sup != "All":
        df_sup = df_sup[df_sup["risk_level"] == risk_sup]

    if df_sup.empty:
        st.info("No matching suppliers.")
    else:
        st.write(f"**{len(df_sup)} supplier(s)**")
        st.dataframe(df_sup, use_container_width=True)

# ================= PRODUCTION =================
with tab3:
    st.subheader("Production Performance Analysis")

    col1, col2 = st.columns([2, 1])
    with col1:
        search_prod = st.text_input("🔍 Search material name", key="prod_search")
    with col2:
        risk_prod = st.selectbox("Risk Level", ["All", "HIGH", "MEDIUM", "NORMAL"], key="prod_risk")

    df_prod = df_production_all.copy()
    if search_prod:
        df_prod = df_prod[df_prod["material_name"].str.contains(search_prod, case=False, na=False)]
    if risk_prod != "All":
        df_prod = df_prod[df_prod["risk_level"] == risk_prod]

    if df_prod.empty:
        st.info("No matching production records.")
    else:
        st.write(f"**{len(df_prod)} record(s)**")
        st.dataframe(df_prod, use_container_width=True)

# ================= DELIVERIES =================
with tab4:
    st.subheader("Delivery Status Overview")

    statuses = ["All"] + sorted(df_deliveries_all["delivery_status"].dropna().unique().tolist())
    delivery_filter = st.selectbox("Filter by Status", statuses, key="dlv_status")

    df_dlv = df_deliveries_all.copy()
    if delivery_filter != "All":
        df_dlv = df_dlv[df_dlv["delivery_status"] == delivery_filter]

    if df_dlv.empty:
        st.info("No matching deliveries.")
    else:
        st.write(f"**{len(df_dlv)} delivery record(s)**")
        st.dataframe(df_dlv, use_container_width=True)

# ================= COSTS =================
with tab5:
    st.subheader("Cost Analysis")

    materials_list = ["All"] + sorted(df_costs_all["material_name"].dropna().unique().tolist())
    col1, col2 = st.columns([1, 1])
    with col1:
        mat_filter = st.selectbox("Filter by Material", materials_list, key="cost_mat")
    with col2:
        cost_type_list = ["All"] + sorted(df_costs_all["cost_type"].dropna().unique().tolist())
        cost_type_filter = st.selectbox("Filter by Cost Type", cost_type_list, key="cost_type")

    df_cost = df_costs_all.copy()
    if mat_filter != "All":
        df_cost = df_cost[df_cost["material_name"] == mat_filter]
    if cost_type_filter != "All":
        df_cost = df_cost[df_cost["cost_type"] == cost_type_filter]

    if df_cost.empty:
        st.info("No matching cost records.")
    else:
        st.write(f"**{len(df_cost)} cost record(s)**")
        st.dataframe(df_cost, use_container_width=True)

        st.markdown("#### Cost Trend (Unit Cost over Time)")
        if len(df_cost) > 1:
            pivot = df_cost.pivot_table(
                index="cost_date",
                columns="material_name",
                values="unit_cost",
                aggfunc="mean"
            )
            st.line_chart(pivot)
        else:
            st.info("Not enough data to plot a trend.")

# ================= RISK ALERTS =================
with tab6:
    st.subheader("Risk Alerts Management")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("🔄 Refresh Risk Analysis", type="primary", use_container_width=True):
            with st.spinner("Analyzing all risks..."):
                new_alerts = run_risk_analysis()
            if new_alerts > 0:
                st.success(f"✅ {new_alerts} new alert(s) added!")
                st.rerun()
            else:
                st.info("✅ No new alerts. Everything is up to date.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.radio(
            "Status:",
            ["OPEN", "ACKNOWLEDGED", "RESOLVED", "ALL"],
            horizontal=True,
            key="alert_status"
        )
    with col2:
        risk_filter = st.radio(
            "Risk Level:",
            ["ALL", "HIGH", "MEDIUM", "NORMAL"],
            horizontal=True,
            key="alert_risk"
        )

    where_parts = []
    if status_filter != "ALL":
        where_parts.append(f"status = '{status_filter}'")
    if risk_filter != "ALL":
        where_parts.append(f"risk_level = '{risk_filter}'")

    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    df_alerts_mgmt = run_query(f"""
        SELECT alert_id, alert_type, alert_description,
               risk_level, detected_date, status
        FROM risk_alerts
        {where_clause}
        ORDER BY
            CASE risk_level
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                ELSE 3
            END,
            alert_id DESC;
    """)

    if df_alerts_mgmt.empty:
        st.info("No alerts match this filter.")
    else:
        st.write(f"**{len(df_alerts_mgmt)} alert(s) found**")

        for _, row in df_alerts_mgmt.iterrows():
            alert_id = int(row["alert_id"])
            risk = row["risk_level"]
            status = row["status"]

            icon = "🔴" if risk == "HIGH" else ("🟡" if risk == "MEDIUM" else "🟢")

            with st.expander(f"{icon} #{alert_id} — {row['alert_type']} — {risk} — {status}"):
                st.write(f"**Description:** {row['alert_description']}")
                st.write(f"**Detected:** {row['detected_date']}")

                col1, col2 = st.columns(2)

                if status == "OPEN":
                    with col1:
                        if st.button("👁 Acknowledge", key=f"ack_{alert_id}"):
                            update_alert_status(alert_id, "ACKNOWLEDGED")
                            st.rerun()
                    with col2:
                        if st.button("✅ Resolve", key=f"res_{alert_id}"):
                            update_alert_status(alert_id, "RESOLVED")
                            st.rerun()

                elif status == "ACKNOWLEDGED":
                    with col1:
                        if st.button("✅ Resolve", key=f"res2_{alert_id}"):
                            update_alert_status(alert_id, "RESOLVED")
                            st.rerun()
                    with col2:
                        if st.button("↩ Reopen", key=f"reop_{alert_id}"):
                            update_alert_status(alert_id, "OPEN")
                            st.rerun()

                else:
                    with col1:
                        if st.button("↩ Reopen", key=f"reop2_{alert_id}"):
                            update_alert_status(alert_id, "OPEN")
                            st.rerun()

# ================= DATA ENTRY =================
with tab7:
    st.header("📝 Data Entry")
    st.caption("Add new records manually or upload an Excel file for bulk import.")

    entry_option = st.radio(
        "Choose method:",
        [
            "📄 Manual Entry",
            "📤 Excel Upload (Bulk Import)"
        ],
        horizontal=True
    )

    st.markdown("---")

    # -------------- MANUAL ENTRY --------------
    if entry_option == "📄 Manual Entry":
        manual_option = st.radio(
            "What to add:",
            [
                "Add Supplier",
                "Add Material",
                "Add Inventory",
                "Add Supplier Performance",
                "Add Production",
                "Add Order",
                "Add Delivery"
            ],
            horizontal=True
        )

        st.markdown("---")

        if manual_option == "Add Supplier":
            supplier_form()
        elif manual_option == "Add Material":
            material_form()
        elif manual_option == "Add Inventory":
            inventory_form()
        elif manual_option == "Add Supplier Performance":
            supplier_performance_form()
        elif manual_option == "Add Production":
            production_form()
        elif manual_option == "Add Order":
            order_form()
        elif manual_option == "Add Delivery":
            delivery_form()

    # -------------- EXCEL UPLOAD --------------
    else:
        st.subheader("📤 Bulk Import from Excel")

        st.info(
            "Your Excel file should have these sheets (sheet names are matched "
            "automatically): **Suppliers, Materials, Inventory, "
            "SupplierPerformance, Production**. "
            "Column names should match the template."
        )

        # Download template button
        try:
            template_data = build_template_excel()
            st.download_button(
                label="⬇️ Download Excel Template",
                data=template_data,
                file_name="industrial_data_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error("Could not build template.")
            st.write(e)

        st.markdown("---")

        uploaded = st.file_uploader(
            "Choose your Excel file (.xlsx)",
            type=["xlsx"],
            key="excel_upload"
        )

        if uploaded is not None:
            if st.button("🚀 Import Data", type="primary"):
                with st.spinner("Importing data... please wait..."):
                    try:
                        result = import_excel(uploaded)
                        st.success("✅ Import complete!")
                        st.markdown("### Summary")
                        st.write(f"- **Suppliers** added: {result['suppliers']}")
                        st.write(f"- **Materials** added: {result['materials']}")
                        st.write(f"- **Inventory** records added: {result['inventory']}")
                        st.write(f"- **Supplier Performance** added: {result['performance']}")
                        st.write(f"- **Production** records added: {result['production']}")

                        if result["errors"]:
                            st.warning(f"⚠️ {len(result['errors'])} row(s) had issues:")
                            with st.expander("Show errors"):
                                for err in result["errors"][:50]:
                                    st.write(f"- {err}")

                        st.info("👉 Now go to **🚨 Risk Alerts** tab and click **🔄 Refresh Risk Analysis** to detect risks from your imported data.")
                    except Exception as e:
                        st.error("Import failed.")
                        st.write(e)

# ================= REPORTS =================
with tab8:
    st.header("📄 Reports & Export")
    st.caption("Download reports as Excel or PDF for management meetings.")

    st.subheader("📊 Excel Report (All Data)")
    st.write("Complete workbook with all sections — Inventory, Suppliers, Production, Deliveries, Costs, Alerts.")

    try:
        df_alerts_all = run_query("""
            SELECT alert_id, alert_type, alert_description,
                   risk_level, detected_date, status
            FROM risk_alerts
            ORDER BY alert_id DESC;
        """)

        excel_sheets = {
            "Inventory": df_inventory_all,
            "Suppliers": df_suppliers_all,
            "Production": df_production_all,
            "Deliveries": df_deliveries_all,
            "Costs": df_costs_all,
            "Alerts": df_alerts_all
        }

        excel_data = df_to_excel_bytes(excel_sheets)

        st.download_button(
            label="⬇️ Download Full Excel Report",
            data=excel_data,
            file_name=f"industrial_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error("Could not build Excel report.")
        st.write(e)

    st.markdown("---")

    st.subheader("📄 PDF Executive Summary")
    st.write("Short management-ready summary with KPIs and top risks.")

    try:
        low_inv_only = df_inventory_all[df_inventory_all["status"] == "LOW"]

        pdf_data = build_summary_pdf(
            suppliers_count, materials_count, alerts_count,
            high_count, medium_count,
            low_inv_only, df_suppliers_all, df_production_all, df_deliveries_all
        )

        st.download_button(
            label="⬇️ Download PDF Executive Summary",
            data=pdf_data,
            file_name=f"industrial_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error("Could not build PDF report.")
        st.write(e)