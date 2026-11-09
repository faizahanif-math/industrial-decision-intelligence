"""
Industrial AI Assistant & Decision Intelligence Engine.
Provides dual-mode intelligence:
1. Built-in Real-time Decision Copilot (direct SQL telemetry & rule-based diagnostics - 100% offline, zero setup).
2. Optional Google Gemini LLM Integration (for free-form natural language reasoning with live plant grounding).
"""

import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dashboard_utils import get_connection


def fetch_live_telemetry():
    """Fetches real-time plant telemetry from PostgreSQL database."""
    conn = get_connection()
    telemetry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "counts": {},
        "alerts_high": [],
        "alerts_medium": [],
        "inventory_low": [],
        "suppliers_at_risk": [],
        "production_shortfalls": [],
        "deliveries_delayed": [],
        "health_score": 100,
    }

    try:
        with conn.cursor() as cur:
            # 1. Total counts
            cur.execute("SELECT COUNT(*) FROM suppliers;")
            telemetry["counts"]["suppliers"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM materials;")
            telemetry["counts"]["materials"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM risk_alerts WHERE status = 'OPEN';")
            telemetry["counts"]["open_alerts"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM risk_alerts WHERE status = 'OPEN' AND risk_level = 'HIGH';")
            telemetry["counts"]["high_alerts"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM risk_alerts WHERE status = 'OPEN' AND risk_level = 'MEDIUM';")
            telemetry["counts"]["medium_alerts"] = cur.fetchone()[0]

            # 2. High & Medium Risk Alerts
            cur.execute("""
                SELECT alert_id, alert_type, alert_description, risk_level, detected_date, status
                FROM risk_alerts
                WHERE status = 'OPEN' AND risk_level = 'HIGH'
                ORDER BY alert_id DESC;
            """)
            telemetry["alerts_high"] = cur.fetchall()

            cur.execute("""
                SELECT alert_id, alert_type, alert_description, risk_level, detected_date, status
                FROM risk_alerts
                WHERE status = 'OPEN' AND risk_level = 'MEDIUM'
                ORDER BY alert_id DESC;
            """)
            telemetry["alerts_medium"] = cur.fetchall()

            # 3. Inventory Shortages
            cur.execute("""
                SELECT m.material_name, i.quantity_on_hand, i.reorder_level,
                       (i.reorder_level - i.quantity_on_hand) AS shortage,
                       m.unit, m.unit_cost
                FROM inventory i
                JOIN materials m ON i.material_id = m.material_id
                WHERE i.quantity_on_hand < i.reorder_level
                ORDER BY shortage DESC;
            """)
            telemetry["inventory_low"] = cur.fetchall()

            # 4. Supplier Performance at Risk
            cur.execute("""
                SELECT s.supplier_name, sp.on_time_delivery_rate, sp.quality_score, sp.performance_status
                FROM supplier_performance sp
                JOIN suppliers s ON sp.supplier_id = s.supplier_id
                WHERE sp.on_time_delivery_rate < 85 OR sp.quality_score < 85
                ORDER BY sp.on_time_delivery_rate ASC;
            """)
            telemetry["suppliers_at_risk"] = cur.fetchall()

            # 5. Production Shortfalls
            cur.execute("""
                SELECT m.material_name, p.planned_quantity, p.produced_quantity,
                       ROUND((p.produced_quantity::numeric / NULLIF(p.planned_quantity, 0)) * 100, 1) AS completion_pct,
                       p.production_status
                FROM production p
                JOIN materials m ON p.material_id = m.material_id
                WHERE (p.produced_quantity::numeric / NULLIF(p.planned_quantity, 0)) * 100 < 85
                ORDER BY completion_pct ASC;
            """)
            telemetry["production_shortfalls"] = cur.fetchall()

            # 6. Deliveries Delayed or Late
            cur.execute("""
                SELECT d.delivery_id, d.order_id, d.delivery_status, d.delivery_cost, d.expected_date
                FROM deliveries d
                WHERE d.delivery_status IN ('Late', 'Delayed', 'Pending')
                ORDER BY d.delivery_id DESC;
            """)
            telemetry["deliveries_delayed"] = cur.fetchall()

            # 7. Compute Plant Operational Health Score (0-100)
            deductions = 0
            deductions += telemetry["counts"]["high_alerts"] * 8
            deductions += telemetry["counts"]["medium_alerts"] * 3
            deductions += len(telemetry["inventory_low"]) * 6
            deductions += len(telemetry["production_shortfalls"]) * 5
            telemetry["health_score"] = max(15, min(100, 100 - deductions))

    finally:
        conn.close()

    return telemetry


def format_telemetry_for_llm(telemetry):
    """Formats real-time telemetry into a clean markdown context string for LLM grounding."""
    lines = [
        f"### REAL-TIME INDUSTRIAL TELEMETRY (Timestamp: {telemetry['timestamp']})",
        f"- Plant Health Score: {telemetry['health_score']}/100",
        f"- Open Alerts: {telemetry['counts'].get('open_alerts', 0)} (HIGH: {telemetry['counts'].get('high_alerts', 0)}, MEDIUM: {telemetry['counts'].get('medium_alerts', 0)})",
        f"- Total Suppliers: {telemetry['counts'].get('suppliers', 0)}, Materials Tracked: {telemetry['counts'].get('materials', 0)}",
        "",
        "#### Critical Open High-Risk Alerts:",
    ]
    if telemetry["alerts_high"]:
        for a in telemetry["alerts_high"]:
            lines.append(f"- [Alert #{a[0]}] Type: {a[1]} | Desc: {a[2]} | Date: {a[4]}")
    else:
        lines.append("- None reported. All systems optimal.")

    lines.append("\n#### Low Stock & Inventory Shortages:")
    if telemetry["inventory_low"]:
        for i in telemetry["inventory_low"]:
            lines.append(f"- Material: {i[0]} | On Hand: {i[1]} | Reorder Level: {i[2]} | Shortage: {i[3]} {i[4]} | Unit Cost: ${float(i[5] or 0):.2f}")
    else:
        lines.append("- All inventory above reorder thresholds.")

    lines.append("\n#### Underperforming Suppliers (<85% SLA):")
    if telemetry["suppliers_at_risk"]:
        for s in telemetry["suppliers_at_risk"]:
            lines.append(f"- Supplier: {s[0]} | On-Time Rate: {s[1]}% | Quality Score: {s[2]}% | Status: {s[3]}")
    else:
        lines.append("- All suppliers performing within SLA targets.")

    lines.append("\n#### Production Shortfalls (<85% Target):")
    if telemetry["production_shortfalls"]:
        for p in telemetry["production_shortfalls"]:
            lines.append(f"- Material: {p[0]} | Completion: {p[3]}% (Produced: {p[2]} / Planned: {p[1]}) | Status: {p[4]}")
    else:
        lines.append("- All production batches meet or exceed planned volume.")

    lines.append("\n#### Delayed / Pending Logistics:")
    if telemetry["deliveries_delayed"]:
        for d in telemetry["deliveries_delayed"]:
            lines.append(f"- Delivery #{d[0]} (Order #{d[1]}) | Status: {d[2]} | Cost: ${float(d[3] or 0):.2f} | Expected: {d[4]}")
    else:
        lines.append("- All deliveries on schedule.")

    return "\n".join(lines)


def generate_builtin_response(user_query, telemetry):
    """
    Intelligent built-in decision intelligence responder.
    Executes rule-based semantic analysis against live PostgreSQL plant telemetry.
    Works 100% offline with zero external API dependencies.
    """
    q = user_query.strip().lower()
    t = telemetry

    # 1. Greetings & Capabilities
    if any(k in q for k in ["hello", "hi", "salam", "assalam", "kese ho", "who are you", "help", "kya kar sakte ho", "intro"]):
        return f"""
### 🤖 Industrial Decision Intelligence Copilot
Welcome! I am your real-time **Plant Operations & Decision Intelligence Advisor**.

#### 📊 Live Plant Snapshot:
- **Operational Health Score:** `{t['health_score']}/100` {'🟢 Stable' if t['health_score'] >= 75 else '🟡 Caution' if t['health_score'] >= 50 else '🔴 Critical Risk'}
- **Open Risk Alerts:** `{t['counts'].get('open_alerts', 0)}` (🔴 **{t['counts'].get('high_alerts', 0)} High**, 🟡 **{t['counts'].get('medium_alerts', 0)} Medium**)
- **Critical Inventory Shortages:** `{len(t['inventory_low'])} item(s)`
- **Suppliers Requiring Review:** `{len(t['suppliers_at_risk'])} vendor(s)`
- **Production Lines Below Target:** `{len(t['production_shortfalls'])} line(s)`

#### 💡 You can ask me:
1. **"What are our high risk alerts?"** — Full risk breakdown & urgency
2. **"Which materials are running low?"** — Inventory shortages & reorder recommendations
3. **"Evaluate supplier performance"** — SLA compliance & vendor risk analysis
4. **"Check production bottlenecks"** — Target completion rates & shortfall analysis
5. **"Show delayed deliveries"** — Shipping bottlenecks & associated costs
6. **"Give me an executive summary"** — Comprehensive management briefing
7. **"What is the mitigation action plan?"** — Step-by-step resolution roadmap
"""

    # 2. Critical & High-Risk Alerts
    if any(k in q for k in ["high risk", "critical", "khatra", "danger", "urgent", "alerts", "open alert", "risk alert"]):
        high_alerts = t["alerts_high"]
        med_alerts = t["alerts_medium"]
        
        if not high_alerts and not med_alerts:
            return "### 🟢 Risk Status: All Clear\nThere are currently **0 open high or medium risk alerts** in the database. All operations are nominal."

        res = f"### 🚨 Industrial Risk Diagnostic\n"
        res += f"Found **{len(high_alerts)} HIGH** and **{len(med_alerts)} MEDIUM** open alerts requiring immediate managerial action.\n\n"
        
        if high_alerts:
            res += "#### 🔴 High Priority Alerts (Action Required within 24h):\n"
            for a in high_alerts:
                res += f"- **Alert #{a[0]} [{a[1]}]:** {a[2]}  \n  *Detected on:* `{a[4]}` | *Status:* `{a[5]}`\n"
        
        if med_alerts:
            res += "\n#### 🟡 Medium Priority Alerts (Monitor & Address):\n"
            for a in med_alerts[:5]:
                res += f"- **Alert #{a[0]} [{a[1]}]:** {a[2]}  \n  *Detected on:* `{a[4]}`\n"
            if len(med_alerts) > 5:
                res += f"  *...and {len(med_alerts) - 5} more medium alerts.*  \n"

        res += """
---
#### 🛠️ Recommended Mitigation Steps:
1. **Acknowledge and assign** critical alerts in the **🚨 Risk Alerts** tab.
2. For inventory and delivery alerts, initiate immediate expediting protocols with procurement.
3. For production shortfalls, verify machine uptime and adjust shift schedules.
"""
        return res

    # 3. Low Inventory & Material Shortages
    if any(k in q for k in ["inventory", "stock", "shortage", "material", "reorder", "maal", "saman", "low stock"]):
        items = t["inventory_low"]
        if not items:
            return "### 📦 Inventory Status: Healthy\nAll materials currently in the database have stock at or above their reorder thresholds."

        res = "### 📦 Critical Inventory Shortage Report\n"
        res += f"The system detected **{len(items)} material(s)** operating below safety reorder levels:\n\n"
        res += "| Material Name | Current Stock | Reorder Level | Deficit Units | Unit Cost | Est. Replenishment Cost |\n"
        res += "| :--- | :---: | :---: | :---: | :---: | :---: |\n"

        total_cost = 0
        for i in items:
            mat = i[0]
            stock = i[1]
            reorder = i[2]
            shortage = i[3]
            unit = i[4] or "units"
            cost = float(i[5] or 0)
            replenish_cost = shortage * cost
            total_cost += replenish_cost
            res += f"| **{mat}** | `{stock} {unit}` | `{reorder} {unit}` | <span style='color:#F43F5E;font-weight:bold;'>-{shortage} {unit}</span> | ${cost:.2f} | **${replenish_cost:,.2f}** |\n"

        res += f"\n**Total Capital Required for Emergency Replenishment:** `${total_cost:,.2f}`\n\n"
        res += """
#### 💡 Procurement Directives:
- **Immediate Reorder:** Trigger purchase orders for materials with maximum deficit.
- **Supplier Buffer:** Negotiate a minimum safety stock consignment agreement with primary vendors.
"""
        return res

    # 4. Supplier Performance & Vendor Reliability
    if any(k in q for k in ["supplier", "vendor", "sla", "vendor rating", "on-time", "quality score", "reliability"]):
        sups = t["suppliers_at_risk"]
        if not sups:
            return "### 🏭 Supplier Performance: Optimal\nAll active suppliers currently meet or exceed the target SLA thresholds (>85% on-time delivery and >85% quality score)."

        res = "### 🏭 Supplier Performance & Vulnerability Diagnostic\n"
        res += f"Detected **{len(sups)} supplier(s)** failing to meet operational reliability thresholds (<85%):\n\n"
        res += "| Supplier Name | On-Time Delivery | Quality Score | Performance Status | Risk Classification |\n"
        res += "| :--- | :---: | :---: | :---: | :---: |\n"

        for s in sups:
            name = s[0]
            ontime = float(s[1] or 0)
            quality = float(s[2] or 0)
            status = s[3]
            risk_label = "🔴 HIGH" if ontime < 70 or quality < 70 else "🟡 MEDIUM"
            res += f"| **{name}** | `{ontime:.1f}%` | `{quality:.1f}%` | `{status}` | **{risk_label}** |\n"

        res += """
---
#### 📋 Corrective Action Items:
1. **Contractual Penalties & Review:** Issue formal notice to vendors with delivery rate < 70%.
2. **Dual-Sourcing Strategy:** Split material allocation 70/30 across backup vendors to mitigate single-supplier dependency.
3. **Incoming Quality Control (IQC):** Enforce 100% inspection on batches from flagged suppliers before entering production lines.
"""
        return res

    # 5. Production Performance & Shortfalls
    if any(k in q for k in ["production", "completion", "produced", "planned", "target", "output", "shortfall", "manufacturing"]):
        prods = t["production_shortfalls"]
        if not prods:
            return "### ⚙️ Production Operations: On Target\nAll monitored manufacturing runs are achieving ≥85% completion of planned quantity."

        res = "### ⚙️ Production Shortfall Analysis\n"
        res += f"Identified **{len(prods)} production line(s)** experiencing capacity bottlenecks or output deficits:\n\n"
        res += "| Material / Item | Planned Units | Produced Units | Completion Rate | Operational Status |\n"
        res += "| :--- | :---: | :---: | :---: | :---: |\n"

        for p in prods:
            mat = p[0]
            planned = p[1]
            produced = p[2]
            completion = float(p[3] or 0)
            status = p[4]
            res += f"| **{mat}** | `{planned:,}` | `{produced:,}` | **{completion:.1f}%** | `{status}` |\n"

        res += """
---
#### 🔧 Root Cause & Remediation Guidelines:
- **Material Constraint:** Verify if raw material inventory shortages are causing line stoppages.
- **Maintenance Audit:** Review machine maintenance logs in `machines` & `maintenance` tables for downtime.
- **Overtime Allocation:** Schedule supplementary shift hours to recover delayed production output.
"""
        return res

    # 6. Deliveries & Supply Chain Logistics
    if any(k in q for k in ["deliver", "shipment", "logistic", "late", "delay", "order", "freight", "transport"]):
        dlvs = t["deliveries_delayed"]
        if not dlvs:
            return "### 🚚 Logistics Status: Nominal\nNo active delivery delays or late orders detected in the system."

        res = "### 🚚 Logistics & Delivery Tracking Diagnostic\n"
        res += f"Found **{len(dlvs)} active shipment(s)** marked as Late, Delayed, or Pending:\n\n"
        res += "| Delivery ID | Order ID | Status | Expected Date | Delivery Cost |\n"
        res += "| :---: | :---: | :---: | :---: | :---: |\n"

        total_dlv_cost = 0
        for d in dlvs:
            did = d[0]
            oid = d[1]
            status = d[2]
            cost = float(d[3] or 0)
            expected = d[4]
            total_dlv_cost += cost
            status_badge = f"<span style='color:#F43F5E;font-weight:bold;'>{status}</span>" if status in ["Late", "Delayed"] else status
            res += f"| `#{did}` | `Order #{oid}` | {status_badge} | `{expected}` | ${cost:,.2f} |\n"

        res += f"\n**Total Committed Logistics Value:** `${total_dlv_cost:,.2f}`\n\n"
        res += """
#### 📍 Supply Chain Logistics Directives:
- Expedite direct carrier tracking for delayed freight shipments.
- Contact receiving dock managers to prioritize inbound inspection for critical batch components.
"""
        return res

    # 7. Executive Summary / Full Diagnostic Briefing
    if any(k in q for k in ["executive", "summary", "report", "overview", "overall", "health", "briefing", "score", "status"]):
        score = t["health_score"]
        status_word = "EXCELLENT" if score >= 85 else "ACCEPTABLE" if score >= 70 else "ELEVATED RISK" if score >= 50 else "CRITICAL VULNERABILITY"
        
        return f"""
### 📋 Executive Decision Intelligence Briefing
**Assessment Timestamp:** `{t['timestamp']}`  
**Plant Health Index:** **`{score}/100`** — **{status_word}**

---
#### 1. Core Key Performance Indicators (KPIs)
- **Active Suppliers:** `{t['counts'].get('suppliers', 0)}` | **Materials Tracked:** `{t['counts'].get('materials', 0)}`
- **Total Open Risk Alerts:** `{t['counts'].get('open_alerts', 0)}`
  - 🔴 High Urgency: `{t['counts'].get('high_alerts', 0)}`
  - 🟡 Medium Urgency: `{t['counts'].get('medium_alerts', 0)}`
- **Deficit Inventory Lines:** `{len(t['inventory_low'])}` items
- **High-Risk Suppliers:** `{len(t['suppliers_at_risk'])}` vendors
- **Production Lines Below Target:** `{len(t['production_shortfalls'])}` runs
- **Delayed Shipments:** `{len(t['deliveries_delayed'])}` orders

---
#### 2. Top Strategic Vulnerabilities
1. **Supply Continuity Risk:** {f"{len(t['inventory_low'])} critical inventory lines are below safety threshold." if t['inventory_low'] else "Inventory buffer levels are stable."}
2. **Vendor Quality & Delivery Compliance:** {f"{len(t['suppliers_at_risk'])} suppliers have on-time delivery or quality compliance rates below 85%." if t['suppliers_at_risk'] else "Supplier compliance within acceptable boundaries."}
3. **Fulfillment Deadlines:** {f"{len(t['deliveries_delayed'])} delivery consignments are currently delayed or pending transit." if t['deliveries_delayed'] else "Logistics schedules operating on time."}

---
#### 3. Executive Recommendation Summary
- Immediately approve emergency reorders for materials with critical deficits.
- Mandate formal vendor remediation meetings for suppliers below 70% reliability.
- Re-balance production floor schedules to compensate for current assembly shortfalls.
"""

    # 8. Action Plan & Recommendations
    if any(k in q for k in ["recommend", "action", "plan", "kya karu", "solution", "mitigat", "next step", "tarkeeb"]):
        return f"""
### 💡 Strategic Industrial Risk Mitigation Roadmap

Based on dynamic analysis of real-time plant metrics, here is the prioritized action roadmap:

#### ⚡ Tier 1: Immediate Actions (Next 0 - 24 Hours)
1. **Resolve Critical Open Alerts:** Review and triage `{t['counts'].get('high_alerts', 0)}` high-risk alerts in the **🚨 Risk Alerts** tab.
2. **Replenish Low Inventory:** Place immediate purchase requisitions for `{len(t['inventory_low'])}` stock items below reorder level.
3. **Carrier Escalation:** Contact freight forwarders for `{len(t['deliveries_delayed'])}` delayed shipments to confirm ETA.

#### 📅 Tier 2: Operational Adjustments (Days 2 - 7)
1. **Supplier Performance Review:** Schedule SLA reviews with vendors scoring below 85% on-time rate.
2. **Production Line Balancing:** Adjust labor allocations to recover completion deficits on lagging production runs.
3. **Inventory Buffer Recalibration:** Recalculate minimum safety stock formulas based on latest delivery delay patterns.

#### 🎯 Tier 3: Strategic Resilience (Days 8 - 30)
1. **Dual-Sourcing Implementation:** Establish qualified secondary suppliers for critical raw materials.
2. **Predictive Maintenance:** Correlate equipment maintenance intervals with production shortfall trends.
3. **Automated Risk Thresholds:** Configure automated webhook notifications when vendor scores drop below 80%.
"""

    # 9. Fallback / General contextual response
    return f"""
### 🏭 Plant Intelligence Telemetry Response
I evaluated your inquiry against current real-time factory database records:

- **Current Plant Health Index:** `{t['health_score']}/100`
- **Active Open Alerts:** `{t['counts'].get('open_alerts', 0)}` (`{t['counts'].get('high_alerts', 0)}` HIGH priority)
- **Low Stock Deficits:** `{len(t['inventory_low'])}` materials below reorder level
- **Supplier SLA Exceptions:** `{len(t['suppliers_at_risk'])}` suppliers below standard

💡 **Suggestions for drill-down:**
- Type **"high risks"** to view all critical alerts and failure points.
- Type **"inventory shortage"** to see depleted materials and reorder quantities.
- Type **"supplier analysis"** to inspect supplier reliability ratings.
- Type **"production shortfall"** to inspect factory throughput.
- Type **"executive summary"** for an executive-ready board report.
"""


def generate_gemini_response(user_query, telemetry, chat_history, api_key):
    """
    Calls Google Gemini AI model grounded with live factory telemetry.
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    telemetry_context = format_telemetry_for_llm(telemetry)
    system_instruction = f"""
You are the elite "Industrial Decision Intelligence Copilot" for an advanced manufacturing and supply chain plant.
You assist plant managers, operations executives, and supply chain analysts in making high-precision operational decisions.

GROUNDING PLANT TELEMETRY:
{telemetry_context}

RULES:
1. Ground your answers strictly in the provided plant telemetry. Mention real metrics, material names, supplier names, and quantities.
2. Structure your answers with clear executive formatting: markdown headers, bold key figures, concise bullet points, and actionable next steps.
3. If the user asks in Urdu or Roman Urdu, reply helpfully in polite Urdu/Roman Urdu mixed with professional business terminology.
4. Always provide practical industrial engineering & supply chain management mitigation recommendations.
"""

    # Build prompt with recent chat context
    messages_payload = [{"role": "user", "parts": [system_instruction + f"\n\nUser Question: {user_query}"]}]
    
    try:
        response = model.generate_content(messages_payload)
        return response.text
    except Exception as e:
        # Fallback to built-in engine if API call fails
        fallback = generate_builtin_response(user_query, telemetry)
        return f"*(Gemini API Notice: {e}. Reverted smoothly to built-in Decision Engine)*\n\n" + fallback


def render_assistant_tab():
    """Renders the comprehensive Industrial AI Assistant tab UI."""
    st.subheader("🤖 Industrial AI Decision Intelligence Copilot")
    st.caption("Real-time decision intelligence engine grounded in live PostgreSQL telemetry.")

    telemetry = fetch_live_telemetry()

    # Top Telemetry Bar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        score = telemetry["health_score"]
        status_color = "normal" if score >= 75 else "off"
        st.metric("Plant Health Index", f"{score}/100", delta=f"{'Healthy' if score >= 75 else 'At Risk'}", delta_color=status_color)
    with c2:
        st.metric("Open Risk Alerts", telemetry["counts"].get("open_alerts", 0), f"🔴 {telemetry['counts'].get('high_alerts', 0)} High")
    with c3:
        st.metric("Low Stock Deficits", f"{len(telemetry['inventory_low'])} items", delta="Shortage", delta_color="inverse")
    with c4:
        st.metric("Suppliers at Risk", f"{len(telemetry['suppliers_at_risk'])} vendors", delta="<85% SLA", delta_color="inverse")

    st.markdown("---")

    # Optional Gemini AI Settings Expander
    with st.expander("⚙️ AI Model & Engine Configuration (Optional Gemini LLM)", expanded=False):
        st.write("By default, the **Built-in Real-time Decision Engine** runs 100% locally and offline from your PostgreSQL database. If you wish to enable extended generative reasoning with Google Gemini, enter your API key below:")
        default_key = os.environ.get("GEMINI_API_KEY", "")
        if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
            default_key = st.secrets["gemini"]["api_key"]
        
        gemini_key = st.text_input("Google Gemini API Key (optional):", value=default_key, type="password", key="assistant_gemini_key")
        if gemini_key:
            st.success("✅ Gemini LLM mode active. Live plant telemetry will be injected into Gemini for deep reasoning.")
        else:
            st.info("ℹ️ Running in **Built-in Decision Engine** mode (fast, deterministic, zero-latency local diagnostic).")

    # Quick Action Prompt Chips
    st.markdown("##### ⚡ Quick Diagnostic Queries:")
    quick_col1, quick_col2, quick_col3, quick_col4, quick_col5, quick_col6 = st.columns(6)
    
    selected_prompt = None
    if quick_col1.button("🚨 Critical Risks", use_container_width=True):
        selected_prompt = "What are our critical high risk alerts and immediate mitigation actions?"
    if quick_col2.button("📦 Low Inventory", use_container_width=True):
        selected_prompt = "Which materials are running below safety reorder level and need replenishment?"
    if quick_col3.button("🏭 Supplier Health", use_container_width=True):
        selected_prompt = "Evaluate supplier performance and list vendors failing SLA targets."
    if quick_col4.button("⚙️ Production Shortfall", use_container_width=True):
        selected_prompt = "Analyze production bottlenecks and shortfalls against planned targets."
    if quick_col5.button("🚚 Delivery Delays", use_container_width=True):
        selected_prompt = "Show all delayed deliveries, freight costs, and supply chain impacts."
    if quick_col6.button("📋 Executive Summary", use_container_width=True):
        selected_prompt = "Generate a full executive management briefing and health scorecard."

    # Initialize chat history
    if "assistant_messages" not in st.session_state:
        st.session_state["assistant_messages"] = [
            {
                "role": "assistant",
                "content": f"**Greetings! I am your Industrial Decision Intelligence Copilot.**\n\nI have established a real-time telemetry link to your PostgreSQL database. Current Plant Health Index is **`{telemetry['health_score']}/100`** with **`{telemetry['counts'].get('open_alerts', 0)}` open risk alerts**.\n\nClick any of the quick diagnostic buttons above or type any custom query below to begin analysis."
            }
        ]

    # Display chat conversation
    for msg in st.session_state["assistant_messages"]:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])

    # Handle quick chip or chat input
    user_input = st.chat_input("Ask about risks, inventory shortages, suppliers, production, or mitigation...")
    active_query = selected_prompt or user_input

    if active_query:
        # Add user message
        st.session_state["assistant_messages"].append({"role": "user", "content": active_query})
        with st.chat_message("user", avatar="👤"):
            st.markdown(active_query)

        # Generate response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing plant telemetry and calculating decision vectors..."):
                if gemini_key and gemini_key.strip():
                    try:
                        reply = generate_gemini_response(active_query, telemetry, st.session_state["assistant_messages"], gemini_key.strip())
                    except Exception as e:
                        reply = generate_builtin_response(active_query, telemetry)
                else:
                    reply = generate_builtin_response(active_query, telemetry)
                
                st.markdown(reply)
                st.session_state["assistant_messages"].append({"role": "assistant", "content": reply})

    # Clear chat option
    st.markdown("---")
    c_clear, c_space = st.columns([1, 4])
    with c_clear:
        if st.button("🗑️ Reset Chat History", use_container_width=True):
            st.session_state["assistant_messages"] = []
            st.rerun()
