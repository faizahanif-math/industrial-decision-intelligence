import streamlit as st
from dashboard_utils import get_connection


def supplier_form():
    st.subheader("➕ Add New Supplier")
    st.caption("Fill this form to add a new supplier to the database.")

    with st.form("add_supplier_form"):
        col1, col2 = st.columns(2)
        with col1:
            supplier_name = st.text_input("Supplier Name *")
            contact_email = st.text_input("Contact Email")
        with col2:
            contact_phone = st.text_input("Contact Phone")
            country = st.text_input("Country", value="Pakistan")

        supplier_status = st.selectbox(
            "Supplier Status", ["Active", "Inactive", "Suspended"])

        submitted = st.form_submit_button("💾 Save Supplier")

        if submitted:
            if not supplier_name.strip():
                st.error("Supplier Name is required.")
                return
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO suppliers
                        (supplier_name, contact_email, contact_phone,
                         country, supplier_status)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING supplier_id;
                    """, (supplier_name.strip(),
                          contact_email.strip() or None,
                          contact_phone.strip() or None,
                          country.strip() or None,
                          supplier_status))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()
                st.success(f"✅ Supplier '{supplier_name}' added! (ID: {new_id})")
                st.balloons()
            except Exception as e:
                st.error("Failed to add supplier.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Suppliers")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT supplier_id, supplier_name, country, supplier_status FROM suppliers ORDER BY supplier_id DESC;")
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe([{"ID": r[0], "Name": r[1], "Country": r[2], "Status": r[3]} for r in rows], use_container_width=True)
        else:
            st.info("No suppliers in database yet.")
    except Exception as e:
        st.error("Could not load suppliers.")
        st.write(e)


def material_form():
    st.subheader("➕ Add New Material")
    st.caption("Fill this form to add a new material to the database.")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name;")
            suppliers = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error("Could not load suppliers.")
        st.write(e)
        return

    if not suppliers:
        st.warning("Please add at least one supplier first.")
        return

    supplier_options = {f"{s[1]} (ID: {s[0]})": s[0] for s in suppliers}

    with st.form("add_material_form"):
        col1, col2 = st.columns(2)
        with col1:
            material_name = st.text_input("Material Name *")
            category = st.text_input("Category (e.g., Metal, Plastic)")
        with col2:
            unit = st.text_input("Unit (e.g., kg, pieces)")
            unit_cost = st.number_input("Unit Cost", min_value=0.0, step=1.0, format="%.2f")

        supplier_choice = st.selectbox("Supplier *", list(supplier_options.keys()))
        submitted = st.form_submit_button("💾 Save Material")

        if submitted:
            if not material_name.strip():
                st.error("Material Name is required.")
                return
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO materials
                        (material_name, category, unit, unit_cost, supplier_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING material_id;
                    """, (material_name.strip(),
                          category.strip() or None,
                          unit.strip() or None,
                          unit_cost,
                          supplier_options[supplier_choice]))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()
                st.success(f"✅ Material '{material_name}' added! (ID: {new_id})")
                st.balloons()
            except Exception as e:
                st.error("Failed to add material.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Materials")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.material_id, m.material_name, m.category, m.unit, m.unit_cost, s.supplier_name
                FROM materials m LEFT JOIN suppliers s ON m.supplier_id = s.supplier_id
                ORDER BY m.material_id DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe([{"ID": r[0], "Name": r[1], "Category": r[2], "Unit": r[3], "Unit Cost": r[4], "Supplier": r[5]} for r in rows], use_container_width=True)
        else:
            st.info("No materials in database yet.")
    except Exception as e:
        st.error("Could not load materials.")
        st.write(e)


def inventory_form():
    st.subheader("➕ Add / Update Inventory")
    st.caption("Track stock level and reorder level of each material.")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT material_id, material_name FROM materials ORDER BY material_name;")
            materials = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error("Could not load materials.")
        st.write(e)
        return

    if not materials:
        st.warning("Please add at least one material first.")
        return

    material_options = {f"{m[1]} (ID: {m[0]})": m[0] for m in materials}

    with st.form("add_inventory_form"):
        material_choice = st.selectbox("Material *", list(material_options.keys()))
        col1, col2 = st.columns(2)
        with col1:
            quantity_on_hand = st.number_input("Quantity on Hand *", min_value=0, step=1)
        with col2:
            reorder_level = st.number_input("Reorder Level *", min_value=0, step=1)

        submitted = st.form_submit_button("💾 Save Inventory")

        if submitted:
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO inventory
                        (material_id, quantity_on_hand, reorder_level, last_updated)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING inventory_id;
                    """, (material_options[material_choice], quantity_on_hand, reorder_level))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()
                st.success(f"✅ Inventory added! (ID: {new_id})")
                st.balloons()
            except Exception as e:
                st.error("Failed to add inventory.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Inventory")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT i.inventory_id, m.material_name, i.quantity_on_hand, i.reorder_level,
                       CASE WHEN i.quantity_on_hand < i.reorder_level THEN 'LOW' ELSE 'OK' END AS status
                FROM inventory i JOIN materials m ON i.material_id = m.material_id
                ORDER BY i.inventory_id DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe([{"ID": r[0], "Material": r[1], "On Hand": r[2], "Reorder": r[3], "Status": r[4]} for r in rows], use_container_width=True)
        else:
            st.info("No inventory records yet.")
    except Exception as e:
        st.error("Could not load inventory.")
        st.write(e)
def supplier_performance_form():
    st.subheader("➕ Add Supplier Performance")
    st.caption("Track on-time delivery and quality score of each supplier.")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name;")
            suppliers = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error("Could not load suppliers.")
        st.write(e)
        return

    if not suppliers:
        st.warning("Please add at least one supplier first.")
        return

    supplier_options = {f"{s[1]} (ID: {s[0]})": s[0] for s in suppliers}

    with st.form("add_perf_form"):
        supplier_choice = st.selectbox("Supplier *", list(supplier_options.keys()))

        col1, col2 = st.columns(2)
        with col1:
            on_time = st.number_input("On-Time Delivery Rate (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
        with col2:
            quality = st.number_input("Quality Score (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")

        submitted = st.form_submit_button("💾 Save Performance")

        if submitted:
            try:
                if on_time < 70 or quality < 70:
                    status = "HIGH"
                elif on_time < 85 or quality < 85:
                    status = "MEDIUM"
                else:
                    status = "NORMAL"

                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO supplier_performance
                        (supplier_id, evaluation_date, on_time_delivery_rate,
                         quality_score, performance_status)
                        VALUES (%s, CURRENT_DATE, %s, %s, %s)
                        RETURNING performance_id;
                    """, (supplier_options[supplier_choice], on_time, quality, status))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()

                st.success(f"✅ Performance added! (ID: {new_id}) — Risk Level: **{status}**")
                st.balloons()
            except Exception as e:
                st.error("Failed to add performance.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Supplier Performance")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sp.performance_id, s.supplier_name,
                       sp.on_time_delivery_rate, sp.quality_score,
                       sp.performance_status, sp.evaluation_date
                FROM supplier_performance sp
                JOIN suppliers s ON sp.supplier_id = s.supplier_id
                ORDER BY sp.performance_id DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe([{"ID": r[0], "Supplier": r[1], "On-Time %": r[2], "Quality %": r[3], "Status": r[4], "Date": r[5]} for r in rows], use_container_width=True)
        else:
            st.info("No performance records yet.")
    except Exception as e:
        st.error("Could not load performance.")
        st.write(e)


def production_form():
    st.subheader("➕ Add Production Record")
    st.caption("Track planned vs produced quantity of each material.")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT material_id, material_name FROM materials ORDER BY material_name;")
            materials = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error("Could not load materials.")
        st.write(e)
        return

    if not materials:
        st.warning("Please add at least one material first.")
        return

    material_options = {f"{m[1]} (ID: {m[0]})": m[0] for m in materials}

    with st.form("add_production_form"):
        material_choice = st.selectbox("Material *", list(material_options.keys()))

        col1, col2 = st.columns(2)
        with col1:
            planned = st.number_input("Planned Quantity *", min_value=1, step=1)
        with col2:
            produced = st.number_input("Produced Quantity *", min_value=0, step=1)

        status = st.selectbox(
            "Production Status",
            ["Completed", "In Progress", "Delayed", "Pending"]
        )

        submitted = st.form_submit_button("💾 Save Production")

        if submitted:
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO production
                        (material_id, planned_quantity, produced_quantity,
                         production_date, production_status)
                        VALUES (%s, %s, %s, CURRENT_DATE, %s)
                        RETURNING production_id;
                    """, (material_options[material_choice],
                          planned, produced, status))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()

                completion = (produced / planned) * 100
                if completion < 70:
                    risk = "🔴 HIGH"
                elif completion < 85:
                    risk = "🟡 MEDIUM"
                else:
                    risk = "🟢 NORMAL"

                st.success(f"✅ Production added! (ID: {new_id}) — Completion: {completion:.1f}% — Risk: {risk}")
                st.balloons()
            except Exception as e:
                st.error("Failed to add production.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Production Records")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.production_id, m.material_name,
                       p.planned_quantity, p.produced_quantity,
                       ROUND((p.produced_quantity::numeric / p.planned_quantity) * 100, 2) AS completion,
                       p.production_status
                FROM production p
                JOIN materials m ON p.material_id = m.material_id
                ORDER BY p.production_id DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe(
                [{"ID": r[0], "Material": r[1], "Planned": r[2],
                  "Produced": r[3], "Completion %": r[4], "Status": r[5]} for r in rows],
                use_container_width=True
            )
        else:
            st.info("No production records yet.")
    except Exception as e:
        st.error("Could not load production.")
        st.write(e)


def order_form():
    st.subheader("➕ Add New Order")
    st.caption("Track customer orders for each material.")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT material_id, material_name FROM materials ORDER BY material_name;")
            materials = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error("Could not load materials.")
        st.write(e)
        return

    if not materials:
        st.warning("Please add at least one material first.")
        return

    material_options = {f"{m[1]} (ID: {m[0]})": m[0] for m in materials}

    with st.form("add_order_form"):
        material_choice = st.selectbox("Material *", list(material_options.keys()))
        quantity = st.number_input("Quantity Ordered *", min_value=1, step=1)
        expected_date = st.date_input("Expected Delivery Date")
        status = st.selectbox(
            "Order Status",
            ["Pending", "Confirmed", "In Production", "Completed", "Cancelled"]
        )

        submitted = st.form_submit_button("💾 Save Order")

        if submitted:
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO orders
                        (material_id, quantity_ordered, order_date,
                         expected_delivery_date, order_status)
                        VALUES (%s, %s, CURRENT_DATE, %s, %s)
                        RETURNING order_id;
                    """, (material_options[material_choice],
                          quantity, expected_date, status))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()

                st.success(f"✅ Order added! (ID: {new_id})")
                st.balloons()
            except Exception as e:
                st.error("Failed to add order.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Orders")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, m.material_name, o.quantity_ordered,
                       o.order_date, o.expected_delivery_date, o.order_status
                FROM orders o
                JOIN materials m ON o.material_id = m.material_id
                ORDER BY o.order_id DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe(
                [{"ID": r[0], "Material": r[1], "Quantity": r[2],
                  "Order Date": r[3], "Expected": r[4], "Status": r[5]} for r in rows],
                use_container_width=True
            )
        else:
            st.info("No orders yet.")
    except Exception as e:
        st.error("Could not load orders.")
        st.write(e)


def delivery_form():
    st.subheader("➕ Add Delivery Record")
    st.caption("Track deliveries against orders.")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, m.material_name, o.quantity_ordered
                FROM orders o
                JOIN materials m ON o.material_id = m.material_id
                ORDER BY o.order_id DESC;
            """)
            orders = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error("Could not load orders.")
        st.write(e)
        return

    if not orders:
        st.warning("Please add at least one order first.")
        return

    order_options = {f"Order #{o[0]} — {o[1]} ({o[2]} units)": o[0] for o in orders}

    with st.form("add_delivery_form"):
        order_choice = st.selectbox("Order *", list(order_options.keys()))

        col1, col2 = st.columns(2)
        with col1:
            delivery_date = st.date_input("Delivery Date")
        with col2:
            expected_date = st.date_input("Expected Date")

        col3, col4 = st.columns(2)
        with col3:
            delivery_status = st.selectbox(
                "Delivery Status",
                ["Delivered", "In Transit", "Pending", "Late", "Delayed"]
            )
        with col4:
            delivery_cost = st.number_input("Delivery Cost", min_value=0.0, step=1.0, format="%.2f")

        submitted = st.form_submit_button("💾 Save Delivery")

        if submitted:
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO deliveries
                        (order_id, delivery_date, expected_date,
                         delivery_status, delivery_cost)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING delivery_id;
                    """, (order_options[order_choice],
                          delivery_date, expected_date,
                          delivery_status, delivery_cost))
                    new_id = cur.fetchone()[0]
                    conn.commit()
                conn.close()

                risk_msg = ""
                if delivery_status in ["Late", "Delayed"]:
                    risk_msg = " 🔴 HIGH risk"
                elif delivery_status in ["Pending", "In Transit"]:
                    risk_msg = " 🟡 MEDIUM risk"
                else:
                    risk_msg = " 🟢 NORMAL"

                st.success(f"✅ Delivery added! (ID: {new_id}) —{risk_msg}")
                st.balloons()
            except Exception as e:
                st.error("Failed to add delivery.")
                st.write(e)

    st.markdown("---")
    st.subheader("📋 Current Deliveries")

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.delivery_id, d.order_id, d.delivery_date,
                       d.expected_date, d.delivery_status, d.delivery_cost
                FROM deliveries d
                ORDER BY d.delivery_id DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        if rows:
            st.dataframe(
                [{"ID": r[0], "Order": r[1], "Delivery Date": r[2],
                  "Expected": r[3], "Status": r[4], "Cost": r[5]} for r in rows],
                use_container_width=True
            )
        else:
            st.info("No deliveries yet.")
    except Exception as e:
        st.error("Could not load deliveries.")
        st.write(e)        