import streamlit as st
import pandas as pd
import numpy as np
from snowflake.snowpark.context import get_active_session
from datetime import date
from io import BytesIO

session = get_active_session()

st.set_page_config(layout="wide", page_title="Profit Centre")

# --- Custom CSS for better UI ---
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    [data-testid="stSidebar"] { background: #0B3D6E !important; }
    [data-testid="stSidebar"] * { color: #b8c7d9 !important; font-size: 13px; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { background: transparent; border: none; border-left: 3px solid transparent; border-radius: 0; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background: rgba(255,255,255,0.05); border-left-color: #5ba3d9; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] { background: rgba(255,255,255,0.1); border-left-color: #ffffff; color: #ffffff !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08) !important; }
    h1 { color: #1B2B44 !important; font-weight: 700 !important; font-family: 'Segoe UI', sans-serif; }
    h2 { color: #1B2B44 !important; font-weight: 600 !important; border: none; }
    h3 { color: #333333 !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 2px solid #e8ebef; border-radius: 0; }
    .stTabs [data-baseweb="tab"] { background: transparent; border-radius: 0; font-weight: 500; font-size: 13px; color: #6b7a8d; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: transparent !important; color: #1B2B44 !important; border-bottom: 2px solid #1B2B44 !important; font-weight: 600; box-shadow: none; }
    div[data-testid="stForm"] { background: #ffffff; border: 1px solid #e8ebef; border-radius: 4px; }
    .streamlit-expanderHeader { background: #f7f8fa; border-radius: 4px; font-weight: 600; font-size: 13px; color: #1B2B44 !important; }
    .stButton > button[kind="primary"] { background: #0B3D6E !important; color: white !important; border: none; border-radius: 4px; font-weight: 500; font-size: 12px; }
    .stButton > button[kind="primary"]:hover { background: #094e8a !important; }
    .stButton > button[kind="secondary"] { background: transparent !important; border: 1px solid #d9534f !important; color: #d9534f !important; border-radius: 4px; font-size: 12px; }
    .stButton > button[kind="secondary"]:hover { background: #fef5f5 !important; }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] { border: 1px solid #dde2e8; border-radius: 2px; }
    [data-testid="stMetric"] { background: #f7f8fa; border: 1px solid #e8ebef; border-radius: 4px; }
    [data-testid="stMetricLabel"] { color: #6b7a8d !important; font-size: 10px !important; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #1B2B44 !important; font-weight: 700 !important; }
    .stSelectbox > div > div, .stTextInput > div > div > input, .stNumberInput > div > div > input { border-radius: 4px; border-color: #dde2e8; font-size: 13px; }
    label { font-size: 12px !important; color: #4a5568 !important; font-weight: 500 !important; }
    hr { border: none; height: 1px; background: #e8ebef; }
    [data-testid="stFileUploader"] { background: #f7f8fa; border: 1px dashed #c5cdd8; border-radius: 4px; }
    .stDownloadButton > button { background: #f7f8fa !important; border: 1px solid #dde2e8 !important; color: #1B2B44 !important; border-radius: 4px; font-size: 12px; }
    .stDownloadButton > button:hover { background: #edf0f3 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="margin:0 0 16px 0; font-size:22px !important; color:#1B2B44 !important; font-weight:700;">Profit Centre</h1>', unsafe_allow_html=True)
import os
_logo_path = os.path.join(os.path.dirname(__file__), ".streamlit", "logo-clbs- (1).png")
if os.path.exists(_logo_path):
    st.sidebar.image(_logo_path, use_container_width=True)
st.sidebar.markdown('<p style="font-size:10px; letter-spacing:1px; opacity:0.5; text-transform:uppercase; color:#8a9bb5 !important;">Navigation</p>', unsafe_allow_html=True)
menu = st.sidebar.radio("Navigation", ["Employee", "SOW", "Dashboard"], label_visibility="collapsed")


# --- HELPERS ---
def normalize_columns(df):
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    return df


def _merge_sow_data(bulk_master_df, bulk_details_df):
    required_master_cols = {"SOW_NO", "SOW_NAME", "SOW_VALUE", "START_DATE", "END_DATE", "PROJECT_NAME"}
    required_detail_cols = {"SOW_NO", "EMP_ID", "SKILL", "ROLE", "START_DATE", "END_DATE", "RATE"}
    missing = []
    if not bulk_master_df.empty:
        missing_m = required_master_cols - set(bulk_master_df.columns)
        if missing_m:
            missing.append(f"SOW Master missing columns: {', '.join(sorted(missing_m))}")
    if not bulk_details_df.empty:
        missing_d = required_detail_cols - set(bulk_details_df.columns)
        if missing_d:
            missing.append(f"SOW Details missing columns: {', '.join(sorted(missing_d))}")
    if missing:
        return 0, 0, missing

    count_m = 0
    count_d = 0
    if not bulk_master_df.empty:
        for _, r in bulk_master_df.iterrows():
            sow_no = str(r.get("SOW_NO", "")).strip()
            if not sow_no:
                continue
            sow_name = str(r.get("SOW_NAME", ""))
            sow_val = float(r.get("SOW_VALUE", 0)) if pd.notnull(r.get("SOW_VALUE")) else 0
            s_dt = str(r.get("START_DATE", date.today()))
            e_dt = str(r.get("END_DATE", date.today()))
            proj = str(r.get("PROJECT_NAME", ""))
            session.sql(f"""
                MERGE INTO CL_DATA.PROFIT_CENTRE.SOW_MASTER tgt
                USING (SELECT '{sow_no}' AS sow_no) src
                ON tgt.sow_no = src.sow_no
                WHEN MATCHED THEN UPDATE SET
                    sow_name='{sow_name}', sow_value={sow_val},
                    start_date='{s_dt}', end_date='{e_dt}', project_name='{proj}'
                WHEN NOT MATCHED THEN INSERT
                VALUES('{sow_no}','{sow_name}',{sow_val},'{s_dt}','{e_dt}','{proj}')
            """).collect()
            count_m += 1
    if not bulk_details_df.empty:
        # Load master date ranges for validation
        master_dates = {}
        if not bulk_master_df.empty:
            for _, mr in bulk_master_df.iterrows():
                m_sow = str(mr.get("SOW_NO", "")).strip()
                if m_sow:
                    master_dates[m_sow] = (
                        pd.to_datetime(mr.get("START_DATE")).date() if pd.notnull(mr.get("START_DATE")) else None,
                        pd.to_datetime(mr.get("END_DATE")).date() if pd.notnull(mr.get("END_DATE")) else None
                    )
        # Also fetch existing masters from DB
        existing_masters = session.sql("SELECT SOW_NO, START_DATE, END_DATE FROM CL_DATA.PROFIT_CENTRE.SOW_MASTER").to_pandas()
        for _, em in existing_masters.iterrows():
            sow_key = str(em["SOW_NO"]).strip()
            if sow_key not in master_dates:
                master_dates[sow_key] = (
                    pd.to_datetime(em["START_DATE"]).date() if pd.notnull(em["START_DATE"]) else None,
                    pd.to_datetime(em["END_DATE"]).date() if pd.notnull(em["END_DATE"]) else None
                )

        date_violations = []
        for _, r in bulk_details_df.iterrows():
            sow_no = str(r.get("SOW_NO", "")).strip()
            emp_id = str(r.get("EMP_ID", "")).strip()
            if not sow_no or not emp_id:
                continue
            skill = str(r.get("SKILL", ""))
            role = str(r.get("ROLE", ""))
            s_dt = str(r.get("START_DATE", date.today()))
            e_dt = str(r.get("END_DATE", date.today()))
            rate = float(r.get("RATE", 0)) if pd.notnull(r.get("RATE")) else 0

            # Validate dates against master range
            if sow_no in master_dates:
                m_start, m_end = master_dates[sow_no]
                det_start = pd.to_datetime(s_dt).date()
                det_end = pd.to_datetime(e_dt).date()
                if m_start and det_start < m_start:
                    date_violations.append(f"{emp_id} (SOW {sow_no}): start {det_start} < master start {m_start}")
                    continue
                if m_end and det_end > m_end:
                    date_violations.append(f"{emp_id} (SOW {sow_no}): end {det_end} > master end {m_end}")
                    continue

            session.sql(f"""
                MERGE INTO CL_DATA.PROFIT_CENTRE.SOW_DETAILS tgt
                USING (SELECT '{sow_no}' AS sow_no, '{emp_id}' AS emp_id) src
                ON tgt.sow_no = src.sow_no AND tgt.emp_id = src.emp_id
                WHEN MATCHED THEN UPDATE SET
                    skill='{skill}', role='{role}',
                    start_date='{s_dt}', end_date='{e_dt}', rate={rate}
                WHEN NOT MATCHED THEN INSERT
                VALUES('{sow_no}','{emp_id}','{skill}','{role}','{s_dt}','{e_dt}',{rate})
            """).collect()
            count_d += 1
        if date_violations:
            missing.extend([f"Date range violation: {v}" for v in date_violations])
    return count_m, count_d, missing


def _merge_employees(bulk_emp_df):
    required_cols = {"EMP_ID", "EMP_NAME", "PHONE_NO", "GRADE", "LOCATION", "COUNTRY", "START_DATE", "END_DATE", "PILLAR_ID"}
    missing_cols = required_cols - set(bulk_emp_df.columns)
    if missing_cols:
        return 0, list(sorted(missing_cols))

    count = 0
    for _, r in bulk_emp_df.iterrows():
        emp_id = str(r.get("EMP_ID", "")).strip()
        if not emp_id:
            continue
        emp_name = str(r.get("EMP_NAME", ""))
        phone = str(r.get("PHONE_NO", ""))
        grade = str(r.get("GRADE", ""))
        location = str(r.get("LOCATION", ""))
        country = str(r.get("COUNTRY", ""))
        s_dt = str(r.get("START_DATE", date.today()))
        e_dt = str(r.get("END_DATE", date.today()))
        p_id = int(r.get("PILLAR_ID", 0)) if pd.notnull(r.get("PILLAR_ID")) else 0
        session.sql(f"""
            MERGE INTO CL_DATA.PROFIT_CENTRE.EMPLOYEE tgt
            USING (SELECT '{emp_id}' AS emp_id) src
            ON tgt.emp_id = src.emp_id
            WHEN MATCHED THEN UPDATE SET
                emp_name='{emp_name}', phone_no='{phone}', grade='{grade}',
                location='{location}', country='{country}',
                start_date='{s_dt}', end_date='{e_dt}', pillar_id={p_id}
            WHEN NOT MATCHED THEN INSERT
            VALUES('{emp_id}','{emp_name}','{phone}','{grade}','{location}','{country}','{s_dt}','{e_dt}',{p_id})
        """).collect()
        count += 1
    return count, []


def _save_monthly_snapshot(year, month, sum_rev, sum_cost, sum_margin, sum_margin_pct):
    session.sql(f"DELETE FROM CL_DATA.PROFIT_CENTRE.MONTHLY_SNAPSHOT WHERE SNAPSHOT_YEAR = {year} AND SNAPSHOT_MONTH = {month}").collect()
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        session.sql(f"""
            INSERT INTO CL_DATA.PROFIT_CENTRE.MONTHLY_SNAPSHOT (SNAPSHOT_YEAR, SNAPSHOT_MONTH, QUARTER, REVENUE, COST, MARGIN, MARGIN_PCT)
            VALUES ({year}, {month}, '{q}', {sum_rev[q]}, {sum_cost[q]}, {sum_margin[q]}, {sum_margin_pct[q]})
        """).collect()


def _load_previous_snapshot(year, current_month):
    prev_month = current_month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year = year - 1
    prev_rev = {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0}
    prev_cost = {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0}
    prev_margin = {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0}
    prev_margin_pct = {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0}
    try:
        df = session.sql(f"""
            SELECT QUARTER, REVENUE, COST, MARGIN, MARGIN_PCT
            FROM CL_DATA.PROFIT_CENTRE.MONTHLY_SNAPSHOT
            WHERE SNAPSHOT_YEAR = {prev_year} AND SNAPSHOT_MONTH = {prev_month}
        """).to_pandas()
        if not df.empty:
            for _, row in df.iterrows():
                q = row["QUARTER"]
                prev_rev[q] = row["REVENUE"]
                prev_cost[q] = row["COST"]
                prev_margin[q] = row["MARGIN"]
                prev_margin_pct[q] = row["MARGIN_PCT"]
    except Exception:
        pass
    return prev_rev, prev_cost, prev_margin, prev_margin_pct


def load_employees():
    return session.sql("""
        SELECT e.EMP_ID, e.EMP_NAME, e.PHONE_NO, e.GRADE, e.LOCATION, e.COUNTRY,
               e.START_DATE, e.END_DATE, e.PILLAR_ID, p.PILLAR_NAME
        FROM CL_DATA.PROFIT_CENTRE.EMPLOYEE e
        LEFT JOIN CL_DATA.PROFIT_CENTRE.PILLAR p ON e.PILLAR_ID = p.PILLAR_ID
        ORDER BY e.EMP_ID
    """).to_pandas()


def load_sow_masters():
    return session.sql("""
        SELECT SOW_NO, SOW_NAME, SOW_VALUE, START_DATE, END_DATE, PROJECT_NAME
        FROM CL_DATA.PROFIT_CENTRE.SOW_MASTER
        ORDER BY SOW_NO
    """).to_pandas()


def load_sow_details(sow_no):
    return session.sql(f"""
        SELECT sd.SOW_NO, sd.EMP_ID, sd.SKILL, sd.ROLE, sd.START_DATE, sd.END_DATE, sd.RATE,
               sm.PROJECT_NAME
        FROM CL_DATA.PROFIT_CENTRE.SOW_DETAILS sd
        LEFT JOIN CL_DATA.PROFIT_CENTRE.SOW_MASTER sm ON sd.SOW_NO = sm.SOW_NO
        WHERE sd.SOW_NO = '{sow_no}'
        ORDER BY sd.EMP_ID
    """).to_pandas()


# ============================================================
# EMPLOYEE SECTION
# ============================================================
if menu == "Employee":
    st.header("Employee")

    pillar_df = session.sql("SELECT pillar_id, pillar_name FROM CL_DATA.PROFIT_CENTRE.PILLAR").to_pandas()
    pillar_map = dict(zip(pillar_df["PILLAR_NAME"], pillar_df["PILLAR_ID"]))
    pillar_id_to_name = dict(zip(pillar_df["PILLAR_ID"], pillar_df["PILLAR_NAME"]))
    pillar_keys = list(pillar_map.keys())
    grade_list = ["A1", "A2", "B1", "B2"]
    loc_list = ["Offshore", "Onshore"]

    # --- Add New Employee Form ---
    with st.expander("Add New Employee", expanded=False):
        with st.form("add_employee_form", clear_on_submit=True):
            st.subheader("New Employee Entry")
            col1, col2, col3 = st.columns(3)
            with col1:
                new_emp_id = st.text_input("Employee ID *", key="new_emp_id")
                new_emp_name = st.text_input("Name *", key="new_emp_name")
                new_phone = st.text_input("Phone", key="new_phone")
            with col2:
                new_grade = st.selectbox("Grade", grade_list, key="new_grade")
                new_location = st.selectbox("Location", loc_list, key="new_location")
                new_country = st.text_input("Country", key="new_country")
            with col3:
                new_pillar = st.selectbox("Pillar", pillar_keys, key="new_pillar")
                new_start = st.date_input("Start Date", value=date.today(), key="new_start")
                new_end = st.date_input("End Date", value=date.today(), key="new_end")

            submitted = st.form_submit_button("Save Employee", type="primary")
            if submitted:
                if not new_emp_id or not new_emp_name:
                    st.error("Employee ID and Name are required.")
                else:
                    p_id = pillar_map.get(new_pillar, 0)
                    session.sql(f"""
                        MERGE INTO CL_DATA.PROFIT_CENTRE.EMPLOYEE tgt
                        USING (SELECT '{new_emp_id}' AS emp_id) src
                        ON tgt.emp_id = src.emp_id
                        WHEN MATCHED THEN UPDATE SET
                            emp_name = '{new_emp_name}', phone_no = '{new_phone}',
                            grade = '{new_grade}', location = '{new_location}',
                            country = '{new_country}', start_date = '{new_start}',
                            end_date = '{new_end}', pillar_id = {p_id}
                        WHEN NOT MATCHED THEN INSERT
                        VALUES('{new_emp_id}', '{new_emp_name}', '{new_phone}', '{new_grade}',
                               '{new_location}', '{new_country}', '{new_start}', '{new_end}', {p_id})
                    """).collect()
                    st.success(f"Employee '{new_emp_id}' saved successfully!")
                    st.rerun()

    st.divider()

    # --- Employee Grid ---
    st.subheader("Employee List")

    emp_df = load_employees()

    if emp_df.empty:
        st.info("No employees found.")
    else:
        display_df = emp_df[["EMP_ID", "EMP_NAME", "PHONE_NO", "GRADE", "LOCATION",
                             "COUNTRY", "PILLAR_NAME", "START_DATE", "END_DATE"]].copy()
        display_df.columns = ["Emp ID", "Name", "Phone", "Grade", "Location",
                              "Country", "Pillar", "Start Date", "End Date"]
        display_df.insert(0, "✓", False)

        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "✓": st.column_config.CheckboxColumn("✓", default=False, width="small"),
                "Emp ID": st.column_config.TextColumn("Emp ID", required=True),
                "Name": st.column_config.TextColumn("Name", required=True),
                "Phone": st.column_config.TextColumn("Phone"),
                "Grade": st.column_config.SelectboxColumn("Grade", options=grade_list),
                "Location": st.column_config.SelectboxColumn("Location", options=loc_list),
                "Country": st.column_config.TextColumn("Country"),
                "Pillar": st.column_config.SelectboxColumn("Pillar", options=pillar_keys),
                "Start Date": st.column_config.DateColumn("Start Date"),
                "End Date": st.column_config.DateColumn("End Date"),
            },
            key="emp_grid"
        )

        col_save, col_del_selected, col_download = st.columns([1, 1, 2])

        with col_save:
            if st.button("Save All Changes", type="primary", key="save_emp_grid"):
                saved_count = 0
                for _, row in edited_df.iterrows():
                    emp_id = str(row["Emp ID"]).strip() if pd.notnull(row["Emp ID"]) else ""
                    if not emp_id:
                        continue
                    emp_name = str(row["Name"]) if pd.notnull(row["Name"]) else ""
                    phone = str(row["Phone"]) if pd.notnull(row["Phone"]) else ""
                    grade = str(row["Grade"]) if pd.notnull(row["Grade"]) else ""
                    location = str(row["Location"]) if pd.notnull(row["Location"]) else ""
                    country = str(row["Country"]) if pd.notnull(row["Country"]) else ""
                    pillar_name = str(row["Pillar"]) if pd.notnull(row["Pillar"]) else ""
                    p_id = pillar_map.get(pillar_name, 0)
                    start_dt = row["Start Date"] if pd.notnull(row.get("Start Date")) else date.today()
                    end_dt = row["End Date"] if pd.notnull(row.get("End Date")) else date.today()

                    session.sql(f"""
                        MERGE INTO CL_DATA.PROFIT_CENTRE.EMPLOYEE tgt
                        USING (SELECT '{emp_id}' AS emp_id) src
                        ON tgt.emp_id = src.emp_id
                        WHEN MATCHED THEN UPDATE SET
                            emp_name = '{emp_name}', phone_no = '{phone}',
                            grade = '{grade}', location = '{location}',
                            country = '{country}', start_date = '{start_dt}',
                            end_date = '{end_dt}', pillar_id = {p_id}
                        WHEN NOT MATCHED THEN INSERT
                        VALUES('{emp_id}', '{emp_name}', '{phone}', '{grade}',
                               '{location}', '{country}', '{start_dt}', '{end_dt}', {p_id})
                    """).collect()
                    saved_count += 1
                st.success(f"Saved {saved_count} employee record(s).")
                st.rerun()

        with col_del_selected:
            selected_rows = edited_df[edited_df["✓"] == True]
            if st.button(f"Delete Selected ({len(selected_rows)})", type="secondary", key="del_emp_grid"):
                if selected_rows.empty:
                    st.warning("Please select rows using the checkbox column first.")
                else:
                    ids_to_delete = selected_rows["Emp ID"].dropna().tolist()
                    if ids_to_delete:
                        ids_str = ",".join([f"'{eid}'" for eid in ids_to_delete])
                        session.sql(f"DELETE FROM CL_DATA.PROFIT_CENTRE.EMPLOYEE WHERE EMP_ID IN ({ids_str})").collect()
                        st.success(f"Deleted {len(ids_to_delete)} employee(s).")
                        st.rerun()

        with col_download:
            csv_data = emp_df.to_csv(index=False)
            st.download_button("Download Employee List", data=csv_data, file_name="employee_list.csv", mime="text/csv")

    st.divider()

    # --- Bulk Upload Employees ---
    st.markdown('''
    <div style="background:#f7f8fa; border:1px solid #e8ebef; border-radius:6px; padding:16px 20px; margin-top:8px;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="font-size:18px;">📁</span>
            <h3 style="margin:0; font-size:14px !important; color:#1B2B44 !important;">Bulk Upload</h3>
        </div>
        <p style="margin:0; font-size:12px; color:#6b7a8d;">Upload a <b>CSV</b> file to add/update employees in bulk.<br>
        Required columns: <code>EMP_ID, EMP_NAME, PHONE_NO, GRADE, LOCATION, COUNTRY, START_DATE, END_DATE, PILLAR_ID</code></p>
    </div>
    ''', unsafe_allow_html=True)
    st.write("")

    emp_bulk_file = st.file_uploader("Employee CSV", type=["csv"], key="emp_bulk_csv")

    if emp_bulk_file:
        bulk_emp_df = normalize_columns(pd.read_csv(emp_bulk_file))
        st.caption("Employee Upload Preview")
        st.dataframe(bulk_emp_df, use_container_width=True, hide_index=True, height=200)

        if st.button("Upload & Merge Employees", type="primary", key="emp_bulk_csv_btn"):
            count, missing = _merge_employees(bulk_emp_df)
            if missing:
                st.error(f"Upload aborted. Missing columns: {', '.join(missing)}")
            else:
                st.success(f"Upload complete! {count} employee record(s) merged.")
                st.rerun()


# ============================================================
# SOW SECTION
# ============================================================
elif menu == "SOW":
    st.header("SOW")

    proj_df = session.sql("SELECT project_name FROM CL_DATA.PROFIT_CENTRE.PROJECT").to_pandas()
    project_list = proj_df["PROJECT_NAME"].tolist()

    # --- Add New SOW Master ---
    with st.expander("Add New SOW", expanded=False):
        with st.form("add_sow_form", clear_on_submit=True):
            st.subheader("New SOW Entry")
            col1, col2 = st.columns(2)
            with col1:
                new_sow_no = st.text_input("SOW No *", key="new_sow_no")
                new_sow_name = st.text_input("SOW Name *", key="new_sow_name")
                new_sow_val = st.number_input("Value", min_value=0.0, format="%.2f", key="new_sow_val")
            with col2:
                new_sow_proj = st.text_input("Project", key="new_sow_proj")
                new_sow_start = st.date_input("Start Date", value=date.today(), key="new_sow_start")
                new_sow_end = st.date_input("End Date", value=date.today(), key="new_sow_end")

            sow_submitted = st.form_submit_button("Save SOW", type="primary")
            if sow_submitted:
                if not new_sow_no or not new_sow_name:
                    st.error("SOW No and SOW Name are required.")
                else:
                    session.sql(f"""
                        MERGE INTO CL_DATA.PROFIT_CENTRE.SOW_MASTER tgt
                        USING (SELECT '{new_sow_no}' AS sow_no) src
                        ON tgt.sow_no = src.sow_no
                        WHEN MATCHED THEN UPDATE SET
                            sow_name = '{new_sow_name}', sow_value = {new_sow_val},
                            start_date = '{new_sow_start}', end_date = '{new_sow_end}',
                            project_name = '{new_sow_proj}'
                        WHEN NOT MATCHED THEN INSERT
                        VALUES('{new_sow_no}', '{new_sow_name}', {new_sow_val},
                               '{new_sow_start}', '{new_sow_end}', '{new_sow_proj}')
                    """).collect()
                    st.success(f"SOW '{new_sow_no}' saved!")
                    st.rerun()

    st.divider()

    # --- SOW Master Grid ---
    st.subheader("SOW Master List")
    st.caption("Select a SOW to view/edit its details below.")

    sow_master_df = load_sow_masters()

    if sow_master_df.empty:
        st.info("No SOW records found.")
    else:
        sow_display = sow_master_df.copy()
        sow_display.insert(0, "✓", False)

        edited_sow_df = st.data_editor(
            sow_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "✓": st.column_config.CheckboxColumn("✓", default=False, width="small"),
                "SOW_NO": st.column_config.TextColumn("SOW No", required=True),
                "SOW_NAME": st.column_config.TextColumn("SOW Name", required=True),
                "SOW_VALUE": st.column_config.NumberColumn("Value", format="%.2f"),
                "START_DATE": st.column_config.DateColumn("Start Date"),
                "END_DATE": st.column_config.DateColumn("End Date"),
                "PROJECT_NAME": st.column_config.TextColumn("Project"),
            },
            key="sow_master_grid"
        )

        col_save_sow, col_del_sow, col_dl_sow = st.columns([1, 1, 2])

        with col_save_sow:
            if st.button("Save All Changes", type="primary", key="save_sow_grid"):
                saved = 0
                for _, row in edited_sow_df.iterrows():
                    sow_no = str(row["SOW_NO"]).strip() if pd.notnull(row["SOW_NO"]) else ""
                    if not sow_no:
                        continue
                    sow_name = str(row["SOW_NAME"]) if pd.notnull(row["SOW_NAME"]) else ""
                    sow_val = float(row["SOW_VALUE"]) if pd.notnull(row["SOW_VALUE"]) else 0
                    s_date = row["START_DATE"] if pd.notnull(row.get("START_DATE")) else date.today()
                    e_date = row["END_DATE"] if pd.notnull(row.get("END_DATE")) else date.today()
                    proj = str(row["PROJECT_NAME"]) if pd.notnull(row["PROJECT_NAME"]) else ""

                    session.sql(f"""
                        MERGE INTO CL_DATA.PROFIT_CENTRE.SOW_MASTER tgt
                        USING (SELECT '{sow_no}' AS sow_no) src
                        ON tgt.sow_no = src.sow_no
                        WHEN MATCHED THEN UPDATE SET
                            sow_name = '{sow_name}', sow_value = {sow_val},
                            start_date = '{s_date}', end_date = '{e_date}',
                            project_name = '{proj}'
                        WHEN NOT MATCHED THEN INSERT
                        VALUES('{sow_no}', '{sow_name}', {sow_val}, '{s_date}', '{e_date}', '{proj}')
                    """).collect()
                    saved += 1
                st.success(f"Saved {saved} SOW master record(s).")
                st.rerun()

        with col_del_sow:
            selected_sow_rows = edited_sow_df[edited_sow_df["✓"] == True]
            if st.button(f"Delete Selected ({len(selected_sow_rows)})", type="secondary", key="del_sow_grid"):
                if selected_sow_rows.empty:
                    st.warning("Please select rows using the checkbox column first.")
                else:
                    ids_to_del = selected_sow_rows["SOW_NO"].dropna().tolist()
                    if ids_to_del:
                        ids_str = ",".join([f"'{s}'" for s in ids_to_del])
                        session.sql(f"DELETE FROM CL_DATA.PROFIT_CENTRE.SOW_DETAILS WHERE SOW_NO IN ({ids_str})").collect()
                        session.sql(f"DELETE FROM CL_DATA.PROFIT_CENTRE.SOW_MASTER WHERE SOW_NO IN ({ids_str})").collect()
                        st.success(f"Deleted {len(ids_to_del)} SOW(s) and related details.")
                        st.rerun()

        with col_dl_sow:
            csv_sow = sow_master_df.to_csv(index=False)
            st.download_button("Download SOW Master", data=csv_sow,
                               file_name="sow_master_list.csv", mime="text/csv")

        st.divider()

        # --- SOW Details (expand on select) ---
        st.subheader("SOW Details")
        selected_sow = st.selectbox(
            "Select SOW to view details",
            options=["-- Select --"] + sow_master_df["SOW_NO"].tolist(),
            key="selected_sow_for_details"
        )

        if selected_sow and selected_sow != "-- Select --":
            master_row = sow_master_df[sow_master_df["SOW_NO"] == selected_sow].iloc[0]
            st.markdown(f"""
            <div style="background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px; padding:12px 20px; margin-bottom:12px;">
                <table style="width:100%; font-size:13px; border-collapse:collapse;">
                    <tr>
                        <td><b>SOW No:</b> {master_row['SOW_NO']}</td>
                        <td><b>Project:</b> {master_row['PROJECT_NAME']}</td>
                        <td><b>Start:</b> {master_row['START_DATE']}</td>
                    </tr>
                    <tr>
                        <td><b>SOW Name:</b> {master_row['SOW_NAME']}</td>
                        <td><b>Value:</b> {master_row['SOW_VALUE']:,.2f}</td>
                        <td><b>End:</b> {master_row['END_DATE']}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

            existing_emp_ids = session.sql("SELECT EMP_ID FROM CL_DATA.PROFIT_CENTRE.EMPLOYEE ORDER BY EMP_ID").to_pandas()["EMP_ID"].tolist()

            # Add new detail
            master_start = pd.to_datetime(master_row['START_DATE']).date() if pd.notnull(master_row['START_DATE']) else date.today()
            master_end = pd.to_datetime(master_row['END_DATE']).date() if pd.notnull(master_row['END_DATE']) else date.today()

            with st.expander("Add SOW Detail Entry", expanded=False):
                st.info(f"Project: **{master_row['PROJECT_NAME']}** | Allowed date range: **{master_start}** to **{master_end}**")
                with st.form("add_sow_detail_form", clear_on_submit=True):
                    dc1, dc2, dc3 = st.columns(3)
                    with dc1:
                        det_emp = st.selectbox("Employee ID *", options=[""] + existing_emp_ids, key="det_emp_id")
                        det_skill = st.text_input("Skill", key="det_skill")
                    with dc2:
                        det_role = st.text_input("Role", key="det_role")
                        det_rate = st.number_input("Rate", min_value=0.0, format="%.2f", key="det_rate")
                    with dc3:
                        det_start = st.date_input("Start Date", value=master_start, min_value=master_start, max_value=master_end, key="det_start")
                        det_end = st.date_input("End Date", value=master_end, min_value=master_start, max_value=master_end, key="det_end")

                    det_submitted = st.form_submit_button("Save Detail", type="primary")
                    if det_submitted:
                        if not det_emp:
                            st.error("Please select an Employee ID.")
                        elif det_start < master_start or det_end > master_end:
                            st.error(f"Dates must be within SOW Master range: {master_start} to {master_end}")
                        elif det_start > det_end:
                            st.error("Start Date cannot be after End Date.")
                        else:
                            session.sql(f"""
                                MERGE INTO CL_DATA.PROFIT_CENTRE.SOW_DETAILS tgt
                                USING (SELECT '{selected_sow}' AS sow_no, '{det_emp}' AS emp_id) src
                                ON tgt.sow_no = src.sow_no AND tgt.emp_id = src.emp_id
                                WHEN MATCHED THEN UPDATE SET
                                    skill = '{det_skill}', role = '{det_role}',
                                    start_date = '{det_start}', end_date = '{det_end}', rate = {det_rate}
                                WHEN NOT MATCHED THEN INSERT
                                VALUES('{selected_sow}', '{det_emp}', '{det_skill}', '{det_role}',
                                       '{det_start}', '{det_end}', {det_rate})
                            """).collect()
                            st.success("SOW Detail saved!")
                            st.rerun()

            # SOW Details grid
            details_df = load_sow_details(selected_sow)

            if details_df.empty:
                st.info("No details found for this SOW. Add one above.")
            else:
                details_display = details_df.copy()
                details_display.insert(0, "✓", False)

                edited_details = st.data_editor(
                    details_display,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["SOW_NO", "PROJECT_NAME"],
                    column_config={
                        "✓": st.column_config.CheckboxColumn("✓", default=False, width="small"),
                        "SOW_NO": st.column_config.TextColumn("SOW No"),
                        "EMP_ID": st.column_config.SelectboxColumn("Emp ID", options=existing_emp_ids, required=True),
                        "SKILL": st.column_config.TextColumn("Skill"),
                        "ROLE": st.column_config.TextColumn("Role"),
                        "START_DATE": st.column_config.DateColumn("Start Date", min_value=master_start, max_value=master_end),
                        "END_DATE": st.column_config.DateColumn("End Date", min_value=master_start, max_value=master_end),
                        "RATE": st.column_config.NumberColumn("Rate", format="%.2f"),
                        "PROJECT_NAME": st.column_config.TextColumn("Project Name (from Master)"),
                    },
                    key="sow_details_grid"
                )

                cd1, cd2, cd3 = st.columns([1, 1, 2])
                with cd1:
                    if st.button("Save Details", type="primary", key="save_det_grid"):
                        saved = 0
                        invalid_emps = []
                        date_errors = []
                        valid_emp_ids = session.sql("SELECT EMP_ID FROM CL_DATA.PROFIT_CENTRE.EMPLOYEE").to_pandas()["EMP_ID"].tolist()
                        for _, row in edited_details.iterrows():
                            emp_id = str(row["EMP_ID"]).strip() if pd.notnull(row["EMP_ID"]) else ""
                            if not emp_id:
                                continue
                            if emp_id not in valid_emp_ids:
                                invalid_emps.append(emp_id)
                                continue
                            skill = str(row["SKILL"]) if pd.notnull(row["SKILL"]) else ""
                            role = str(row["ROLE"]) if pd.notnull(row["ROLE"]) else ""
                            rate = float(row["RATE"]) if pd.notnull(row["RATE"]) else 0
                            s_dt = row["START_DATE"] if pd.notnull(row.get("START_DATE")) else date.today()
                            e_dt = row["END_DATE"] if pd.notnull(row.get("END_DATE")) else date.today()

                            # Validate dates within SOW Master range
                            s_dt_date = pd.to_datetime(s_dt).date() if not isinstance(s_dt, date) else s_dt
                            e_dt_date = pd.to_datetime(e_dt).date() if not isinstance(e_dt, date) else e_dt
                            if s_dt_date < master_start or e_dt_date > master_end:
                                date_errors.append(f"{emp_id} ({s_dt} - {e_dt})")
                                continue

                            session.sql(f"""
                                MERGE INTO CL_DATA.PROFIT_CENTRE.SOW_DETAILS tgt
                                USING (SELECT '{selected_sow}' AS sow_no, '{emp_id}' AS emp_id) src
                                ON tgt.sow_no = src.sow_no AND tgt.emp_id = src.emp_id
                                WHEN MATCHED THEN UPDATE SET
                                    skill = '{skill}', role = '{role}',
                                    start_date = '{s_dt}', end_date = '{e_dt}', rate = {rate}
                                WHEN NOT MATCHED THEN INSERT
                                VALUES('{selected_sow}', '{emp_id}', '{skill}', '{role}',
                                       '{s_dt}', '{e_dt}', {rate})
                            """).collect()
                            saved += 1
                        if date_errors:
                            st.error(f"Date(s) outside SOW Master range ({master_start} to {master_end}): {', '.join(date_errors)}")
                        if invalid_emps:
                            st.error(f"Employee(s) not found: {', '.join(invalid_emps)}. Please add them in Employee section first.")
                        if saved > 0:
                            st.success(f"Saved {saved} detail record(s).")
                            st.rerun()

                with cd2:
                    selected_det_rows = edited_details[edited_details["✓"] == True]
                    if st.button(f"Delete Selected ({len(selected_det_rows)})", type="secondary", key="del_det_grid"):
                        if selected_det_rows.empty:
                            st.warning("Please select rows using the checkbox column first.")
                        else:
                            ids_to_del = selected_det_rows["EMP_ID"].dropna().tolist()
                            if ids_to_del:
                                ids_str = ",".join([f"'{e}'" for e in ids_to_del])
                                session.sql(f"""
                                    DELETE FROM CL_DATA.PROFIT_CENTRE.SOW_DETAILS
                                    WHERE SOW_NO = '{selected_sow}' AND EMP_ID IN ({ids_str})
                                """).collect()
                                st.success(f"Deleted {len(ids_to_del)} detail(s).")
                                st.rerun()

                with cd3:
                    csv_det = details_df.to_csv(index=False)
                    st.download_button("Download Details", data=csv_det,
                                       file_name=f"sow_details_{selected_sow}.csv", mime="text/csv")

    st.divider()

    # --- Bulk Upload SOW ---

    st.markdown('''
    <div style="background:#f7f8fa; border:1px solid #e8ebef; border-radius:6px; padding:16px 20px; margin-top:8px;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="font-size:18px;">📁</span>
            <h3 style="margin:0; font-size:14px !important; color:#1B2B44 !important;">Bulk Upload</h3>
        </div>
        <p style="margin:0; font-size:12px; color:#6b7a8d;">Upload <b>CSV</b> files for SOW Master and SOW Details</p>
    </div>
    ''', unsafe_allow_html=True)
    st.write("")

    col_m, col_d = st.columns(2)
    with col_m:
        master_file = st.file_uploader("SOW Master CSV", type=["csv"], key="sow_master_csv")
    with col_d:
        details_file = st.file_uploader("SOW Details CSV", type=["csv"], key="sow_details_csv")

    bulk_master_df = pd.DataFrame()
    bulk_details_df = pd.DataFrame()

    if master_file:
        bulk_master_df = normalize_columns(pd.read_csv(master_file))
        st.caption("SOW Master Preview")
        st.dataframe(bulk_master_df, use_container_width=True, hide_index=True, height=150)

    if details_file:
        bulk_details_df = normalize_columns(pd.read_csv(details_file))
        st.caption("SOW Details Preview")
        st.dataframe(bulk_details_df, use_container_width=True, hide_index=True, height=150)

    if (master_file or details_file) and st.button("Upload & Merge All", type="primary", key="sow_bulk_csv_btn"):
        count_m, count_d, missing = _merge_sow_data(bulk_master_df, bulk_details_df)
        if missing:
            for msg in missing:
                st.error(f"Upload aborted. {msg}")
        else:
            st.success(f"Upload complete! SOW Master: {count_m}, SOW Details: {count_d} records merged.")
            st.rerun()


# ============================================================
# DASHBOARD SECTION
# ============================================================
elif menu == "Dashboard":
    st.header("Dashboard")

    current_year = date.today().year
    available_years = [2024, 2025, 2026, 2027, 2028]
    selected_year = st.selectbox(
        "Select Year", available_years,
        index=available_years.index(current_year) if current_year in available_years else 0
    )

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    df = session.sql(f"""
        SELECT e.emp_id, e.emp_name, s.project_name,
               e.grade, e.location,
               sd.start_date AS sow_start_date,
               sd.end_date   AS sow_end_date,
               sd.rate
        FROM CL_DATA.PROFIT_CENTRE.EMPLOYEE e
        LEFT JOIN CL_DATA.PROFIT_CENTRE.SOW_DETAILS sd ON e.emp_id  = sd.emp_id
        LEFT JOIN CL_DATA.PROFIT_CENTRE.SOW_MASTER  s  ON sd.sow_no = s.sow_no
        WHERE YEAR(sd.start_date) = {selected_year}
           OR YEAR(sd.end_date)   = {selected_year}
           OR (sd.start_date <= '{selected_year}-12-31' AND sd.end_date >= '{selected_year}-01-01')
    """).to_pandas()

    cost_cols = []
    rev_cols = []
    project_list_from_data = []
    monthly_rev_totals = {m: 0.0 for m in months}
    monthly_cost_totals = {m: 0.0 for m in months}

    if not df.empty:
        arc = session.sql(f"SELECT grade, arc_rate FROM CL_DATA.PROFIT_CENTRE.ARC_COST_CARD WHERE year = {selected_year}").to_pandas()
        df = df.merge(arc, on="GRADE", how="left")

        df["SOW_START_DATE"] = pd.to_datetime(df["SOW_START_DATE"]).dt.date
        df["SOW_END_DATE"] = pd.to_datetime(df["SOW_END_DATE"]).dt.date

        df["Allocation"] = 100 / df.groupby("EMP_ID")["PROJECT_NAME"].transform("nunique").replace(0, 1)

        df["MH"] = np.where(df["LOCATION"] == "Offshore", 195, 173)
        df["DH"] = np.where(df["LOCATION"] == "Offshore", 9, 8)

        df["Estimated Monthly Cost"] = df["ARC_RATE"] * df["MH"]
        df["Estimated Monthly Revenue"] = df["RATE"] * df["MH"]

        for i, m in enumerate(months, 1):
            start_m = pd.to_datetime(f"{selected_year}-{i:02d}-01")
            end_m = start_m + pd.offsets.MonthEnd(0)

            def calculate_working_days(row, start_m=start_m, end_m=end_m):
                sow_s = row["SOW_START_DATE"]
                sow_e = row["SOW_END_DATE"]
                if pd.isna(sow_s) or pd.isna(sow_e):
                    return 0
                sow_s_dt = pd.to_datetime(sow_s)
                sow_e_dt = pd.to_datetime(sow_e)
                if sow_e_dt < start_m or sow_s_dt > end_m:
                    return 0
                s = max(sow_s_dt, start_m)
                e = min(sow_e_dt, end_m)
                s_date = s.date() if hasattr(s, "date") else s
                e_date = e.date() if hasattr(e, "date") else e
                return np.busday_count(s_date, (e_date + pd.Timedelta(days=1)))

            days = df.apply(calculate_working_days, axis=1)
            c = f"{m}_Cost"
            r = f"{m}_Rev"
            df[c] = days * df["DH"] * df["ARC_RATE"]
            df[r] = days * df["DH"] * df["RATE"]
            cost_cols.append(c)
            rev_cols.append(r)

        df = df.drop_duplicates(subset=["EMP_ID", "PROJECT_NAME"])

        for m in months:
            monthly_rev_totals[m] = df[f"{m}_Rev"].sum()
            monthly_cost_totals[m] = df[f"{m}_Cost"].sum()

        project_list_from_data = df["PROJECT_NAME"].dropna().unique().tolist()

        df = df.rename(columns={
            "EMP_ID": "EE/CT Code", "EMP_NAME": "Name", "PROJECT_NAME": "Project",
            "GRADE": "Grade", "LOCATION": "Location",
            "SOW_START_DATE": "Start Date", "SOW_END_DATE": "End Date",
            "ARC_RATE": "ARC", "RATE": "COR"
        })

        final_cols = [
            "EE/CT Code", "Name", "Project", "Grade", "Allocation", "Location",
            "Start Date", "End Date", "ARC", "COR",
            "Estimated Monthly Cost", "Estimated Monthly Revenue"
        ] + cost_cols + rev_cols

        df = df[final_cols]

    tab1, tab2 = st.tabs(["Team List & Sow", "Firm Revenue"])

    # ============================================================
    # TAB 1: Team List & Sow (existing dashboard)
    # ============================================================
    with tab1:
        if df.empty:
            st.info("No data found for the selected year.")
        else:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            totals = {col: "" for col in df.columns}
            totals["EE/CT Code"] = "TOTAL"
            for col in numeric_cols:
                totals[col] = df[col].sum()

            df_with_totals = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

            def format_number(val):
                if isinstance(val, (int, float)):
                    return f"{val:,.2f}"
                return val

            st.dataframe(
                df_with_totals.style.format(format_number, subset=numeric_cols),
                use_container_width=True,
                height=400
            )

            csv = df_with_totals.to_csv(index=False)
            st.download_button(
                label=f"Download {selected_year} Data as CSV",
                data=csv,
                file_name=f"profit_centre_data_{selected_year}.csv",
                mime="text/csv"
            )

    # ============================================================
    # TAB 2: Firm Revenue
    # ============================================================
    with tab2:
        st.subheader(f"Firm Revenue - {selected_year}")

        if "firm_revenue_data" not in st.session_state:
            st.session_state["firm_revenue_data"] = {}

        state_key = f"firm_rev_{selected_year}"
        if state_key not in st.session_state:
            st.session_state[state_key] = {
                "risk": {},
                "opportunity": {},
                "projects": project_list_from_data if project_list_from_data else []
            }

        # --- Revenue Section (K$) ---
        st.markdown(f"### {selected_year} - Rev (K$)")

        rev_data = []
        for proj in project_list_from_data:
            row = {"Opportunity / Project": proj, "Risk %": 0}
            proj_df = df[df["Project"] == proj] if not df.empty else pd.DataFrame()
            for m in months:
                if not proj_df.empty:
                    row[m] = round(proj_df[f"{m}_Rev"].sum() / 1000, 2)
                else:
                    row[m] = 0.0
            rev_data.append(row)

        if "firm_rev_opp_rows" not in st.session_state:
            st.session_state["firm_rev_opp_rows"] = []

        for opp_row in st.session_state.get("firm_rev_opp_rows", []):
            rev_data.append(opp_row)

        rev_df = pd.DataFrame(rev_data) if rev_data else pd.DataFrame(
            columns=["Opportunity / Project", "Risk %"] + months
        )

        if not rev_df.empty:
            rev_df["Q1"] = rev_df[["Jan", "Feb", "Mar"]].sum(axis=1)
            rev_df["Q2"] = rev_df[["Apr", "May", "Jun"]].sum(axis=1)
            rev_df["Q3"] = rev_df[["Jul", "Aug", "Sep"]].sum(axis=1)
            rev_df["Q4"] = rev_df[["Oct", "Nov", "Dec"]].sum(axis=1)
            rev_df["Total"] = rev_df[months].sum(axis=1)
            rev_df["Risk Adjusted Total"] = 0.0
            rev_df["Post Discount"] = 0.0

        rev_display_cols = ["Opportunity / Project", "Risk %"] + months + ["Q1", "Q2", "Q3", "Q4", "Total", "Risk Adjusted Total", "Post Discount"]

        edited_rev = st.data_editor(
            rev_df[rev_display_cols] if not rev_df.empty else pd.DataFrame(columns=rev_display_cols),
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Opportunity / Project": st.column_config.TextColumn("Opportunity / Project"),
                "Risk %": st.column_config.NumberColumn("Risk %", min_value=0, max_value=100, format="%.0f"),
                "Q1": st.column_config.NumberColumn("Q1", disabled=True, format="%.2f"),
                "Q2": st.column_config.NumberColumn("Q2", disabled=True, format="%.2f"),
                "Q3": st.column_config.NumberColumn("Q3", disabled=True, format="%.2f"),
                "Q4": st.column_config.NumberColumn("Q4", disabled=True, format="%.2f"),
                "Total": st.column_config.NumberColumn("Total", disabled=True, format="%.2f"),
                "Risk Adjusted Total": st.column_config.NumberColumn("Risk Adjusted Total", format="%.2f"),
                "Post Discount": st.column_config.NumberColumn("Post Discount", format="%.2f"),
            },
            key="rev_editor"
        )

        if not edited_rev.empty:
            total_rev_row = {"Opportunity / Project": "Total Revenue"}
            for m in months:
                total_rev_row[m] = edited_rev[m].sum() if m in edited_rev.columns else 0
            total_rev_row["Q1"] = edited_rev["Q1"].sum() if "Q1" in edited_rev.columns else 0
            total_rev_row["Q2"] = edited_rev["Q2"].sum() if "Q2" in edited_rev.columns else 0
            total_rev_row["Q3"] = edited_rev["Q3"].sum() if "Q3" in edited_rev.columns else 0
            total_rev_row["Q4"] = edited_rev["Q4"].sum() if "Q4" in edited_rev.columns else 0
            total_rev_row["Total"] = edited_rev["Total"].sum() if "Total" in edited_rev.columns else 0
            st.markdown(f"**Total Revenue: {total_rev_row['Total']:,.2f} K$**")

        st.divider()

        # --- Cost Section (K$) ---
        st.markdown(f"### {selected_year} - Cost (K$)")

        cost_data = []
        for proj in project_list_from_data:
            row = {"Opportunity / Project": proj, "Risk %": 0}
            proj_df = df[df["Project"] == proj] if not df.empty else pd.DataFrame()
            for m in months:
                if not proj_df.empty:
                    row[m] = round(proj_df[f"{m}_Cost"].sum() / 1000, 2)
                else:
                    row[m] = 0.0
            cost_data.append(row)

        for opp_row in st.session_state.get("firm_rev_opp_rows", []):
            cost_row = {"Opportunity / Project": opp_row["Opportunity / Project"], "Risk %": opp_row.get("Risk %", 0)}
            for m in months:
                cost_row[m] = 0.0
            cost_data.append(cost_row)

        cost_df = pd.DataFrame(cost_data) if cost_data else pd.DataFrame(
            columns=["Opportunity / Project", "Risk %"] + months
        )

        if not cost_df.empty:
            cost_df["Q1"] = cost_df[["Jan", "Feb", "Mar"]].sum(axis=1)
            cost_df["Q2"] = cost_df[["Apr", "May", "Jun"]].sum(axis=1)
            cost_df["Q3"] = cost_df[["Jul", "Aug", "Sep"]].sum(axis=1)
            cost_df["Q4"] = cost_df[["Oct", "Nov", "Dec"]].sum(axis=1)
            cost_df["Total"] = cost_df[months].sum(axis=1)
            cost_df["Risk Adjusted Total"] = 0.0
            cost_df["Post Discount"] = 0.0

        cost_display_cols = ["Opportunity / Project", "Risk %"] + months + ["Q1", "Q2", "Q3", "Q4", "Total", "Risk Adjusted Total", "Post Discount"]

        edited_cost = st.data_editor(
            cost_df[cost_display_cols] if not cost_df.empty else pd.DataFrame(columns=cost_display_cols),
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Opportunity / Project": st.column_config.TextColumn("Opportunity / Project"),
                "Risk %": st.column_config.NumberColumn("Risk %", min_value=0, max_value=100, format="%.0f"),
                "Q1": st.column_config.NumberColumn("Q1", disabled=True, format="%.2f"),
                "Q2": st.column_config.NumberColumn("Q2", disabled=True, format="%.2f"),
                "Q3": st.column_config.NumberColumn("Q3", disabled=True, format="%.2f"),
                "Q4": st.column_config.NumberColumn("Q4", disabled=True, format="%.2f"),
                "Total": st.column_config.NumberColumn("Total", disabled=True, format="%.2f"),
                "Risk Adjusted Total": st.column_config.NumberColumn("Risk Adjusted Total", format="%.2f"),
                "Post Discount": st.column_config.NumberColumn("Post Discount", format="%.2f"),
            },
            key="cost_editor"
        )

        if not edited_cost.empty:
            total_cost_row = {"Opportunity / Project": "Total Cost"}
            for m in months:
                total_cost_row[m] = edited_cost[m].sum() if m in edited_cost.columns else 0
            total_cost_row["Q1"] = edited_cost["Q1"].sum() if "Q1" in edited_cost.columns else 0
            total_cost_row["Q2"] = edited_cost["Q2"].sum() if "Q2" in edited_cost.columns else 0
            total_cost_row["Q3"] = edited_cost["Q3"].sum() if "Q3" in edited_cost.columns else 0
            total_cost_row["Q4"] = edited_cost["Q4"].sum() if "Q4" in edited_cost.columns else 0
            total_cost_row["Total"] = edited_cost["Total"].sum() if "Total" in edited_cost.columns else 0
            st.markdown(f"**Total Cost: {total_cost_row['Total']:,.2f} K$**")

        st.divider()

        # --- Margin Section (K$) ---
        st.markdown(f"### {selected_year} - Margin (K$)")

        if not edited_rev.empty and not edited_cost.empty:
            margin_data = []
            all_projects = edited_rev["Opportunity / Project"].dropna().tolist()
            for proj in all_projects:
                row = {"Opportunity / Project": proj}
                rev_row = edited_rev[edited_rev["Opportunity / Project"] == proj]
                cost_row_data = edited_cost[edited_cost["Opportunity / Project"] == proj]
                for m in months:
                    r_val = rev_row[m].values[0] if not rev_row.empty and m in rev_row.columns else 0
                    c_val = cost_row_data[m].values[0] if not cost_row_data.empty and m in cost_row_data.columns else 0
                    row[m] = r_val - c_val
                margin_data.append(row)

            margin_df = pd.DataFrame(margin_data)
            if not margin_df.empty:
                margin_df["Q1"] = margin_df[["Jan", "Feb", "Mar"]].sum(axis=1)
                margin_df["Q2"] = margin_df[["Apr", "May", "Jun"]].sum(axis=1)
                margin_df["Q3"] = margin_df[["Jul", "Aug", "Sep"]].sum(axis=1)
                margin_df["Q4"] = margin_df[["Oct", "Nov", "Dec"]].sum(axis=1)
                margin_df["Total"] = margin_df[months].sum(axis=1)

            margin_display_cols = ["Opportunity / Project"] + months + ["Q1", "Q2", "Q3", "Q4", "Total"]
            st.dataframe(
                margin_df[margin_display_cols] if not margin_df.empty else pd.DataFrame(columns=margin_display_cols),
                use_container_width=True,
                hide_index=True
            )

            total_margin = margin_df[months].sum().sum() if not margin_df.empty else 0
            st.markdown(f"**Total Margin: {total_margin:,.2f} K$**")

        st.divider()

        # --- % Margin Section ---
        st.markdown(f"### {selected_year} - % Margin")

        if not edited_rev.empty and not edited_cost.empty:
            pct_margin_data = []
            all_projects_pct = edited_rev["Opportunity / Project"].dropna().tolist()
            for proj in all_projects_pct:
                row = {"Opportunity / Project": proj}
                rev_row = edited_rev[edited_rev["Opportunity / Project"] == proj]
                cost_row_data = edited_cost[edited_cost["Opportunity / Project"] == proj]
                for m in months:
                    r_val = rev_row[m].values[0] if not rev_row.empty and m in rev_row.columns else 0
                    c_val = cost_row_data[m].values[0] if not cost_row_data.empty and m in cost_row_data.columns else 0
                    row[m] = ((r_val - c_val) / r_val * 100) if r_val != 0 else 0
                pct_margin_data.append(row)

            pct_margin_df = pd.DataFrame(pct_margin_data)
            if not pct_margin_df.empty:
                for q_name, q_months in [("Q1", ["Jan", "Feb", "Mar"]), ("Q2", ["Apr", "May", "Jun"]),
                                          ("Q3", ["Jul", "Aug", "Sep"]), ("Q4", ["Oct", "Nov", "Dec"])]:
                    q_rev = sum(edited_rev[m].sum() for m in q_months)
                    q_cost = sum(edited_cost[m].sum() for m in q_months)
                    pct_margin_df[q_name] = ((q_rev - q_cost) / q_rev * 100) if q_rev != 0 else 0

                total_rev_all = edited_rev[months].sum().sum()
                total_cost_all = edited_cost[months].sum().sum()
                pct_margin_df["Total"] = ((total_rev_all - total_cost_all) / total_rev_all * 100) if total_rev_all != 0 else 0

            pct_display_cols = ["Opportunity / Project"] + months + ["Q1", "Q2", "Q3", "Q4", "Total"]
            st.dataframe(
                pct_margin_df[pct_display_cols].style.format("{:.2f}%", subset=months + ["Q1", "Q2", "Q3", "Q4", "Total"]) if not pct_margin_df.empty else pd.DataFrame(columns=pct_display_cols),
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # ============================================================
        # SUMMARY SECTION
        # ============================================================
        st.markdown("### Summary")

        if not edited_rev.empty and not edited_cost.empty:
            summary_data = {}

            q_periods = {
                "Q1": ["Jan", "Feb", "Mar"],
                "Q2": ["Apr", "May", "Jun"],
                "Q3": ["Jul", "Aug", "Sep"],
                "Q4": ["Oct", "Nov", "Dec"],
            }

            sum_rev = {}
            sum_cost = {}
            sum_margin = {}
            sum_margin_pct = {}

            for q_name, q_months in q_periods.items():
                q_rev = sum(edited_rev[m].sum() for m in q_months if m in edited_rev.columns)
                q_cost = sum(edited_cost[m].sum() for m in q_months if m in edited_cost.columns)
                q_margin = q_rev - q_cost
                q_margin_pct = (q_margin / q_rev * 100) if q_rev != 0 else 0
                sum_rev[q_name] = round(q_rev, 2)
                sum_cost[q_name] = round(q_cost, 2)
                sum_margin[q_name] = round(q_margin, 2)
                sum_margin_pct[q_name] = round(q_margin_pct, 2)

            total_rev_sum = sum(sum_rev.values())
            total_cost_sum = sum(sum_cost.values())
            total_margin_sum = total_rev_sum - total_cost_sum
            total_margin_pct_sum = (total_margin_sum / total_rev_sum * 100) if total_rev_sum != 0 else 0

            # Q1'-Q4' comparison with last month's snapshot
            current_month = date.today().month
            prev_q_rev, prev_q_cost, prev_q_margin, prev_q_margin_pct = _load_previous_snapshot(selected_year, current_month)
            prev_total_rev = sum(prev_q_rev.values())
            prev_total_cost = sum(prev_q_cost.values())
            prev_total_margin = prev_total_rev - prev_total_cost
            prev_total_margin_pct = (prev_total_margin / prev_total_rev * 100) if prev_total_rev != 0 else 0

            summary_table = pd.DataFrame({
                "": ["Revenue", "Cost", "Margin", "Margin %"],
                "Q1": [sum_rev["Q1"], sum_cost["Q1"], sum_margin["Q1"], f"{sum_margin_pct['Q1']:.2f}%"],
                "Q1'": [round(prev_q_rev["Q1"], 2), round(prev_q_cost["Q1"], 2), round(prev_q_margin["Q1"], 2), f"{prev_q_margin_pct['Q1']:.2f}%"],
                "Q2": [sum_rev["Q2"], sum_cost["Q2"], sum_margin["Q2"], f"{sum_margin_pct['Q2']:.2f}%"],
                "Q2'": [round(prev_q_rev["Q2"], 2), round(prev_q_cost["Q2"], 2), round(prev_q_margin["Q2"], 2), f"{prev_q_margin_pct['Q2']:.2f}%"],
                "Q3": [sum_rev["Q3"], sum_cost["Q3"], sum_margin["Q3"], f"{sum_margin_pct['Q3']:.2f}%"],
                "Q3'": [round(prev_q_rev["Q3"], 2), round(prev_q_cost["Q3"], 2), round(prev_q_margin["Q3"], 2), f"{prev_q_margin_pct['Q3']:.2f}%"],
                "Q4": [sum_rev["Q4"], sum_cost["Q4"], sum_margin["Q4"], f"{sum_margin_pct['Q4']:.2f}%"],
                "Q4'": [round(prev_q_rev["Q4"], 2), round(prev_q_cost["Q4"], 2), round(prev_q_margin["Q4"], 2), f"{prev_q_margin_pct['Q4']:.2f}%"],
                "Total": [round(total_rev_sum, 2), round(total_cost_sum, 2), round(total_margin_sum, 2), f"{total_margin_pct_sum:.2f}%"],
                "Total'": [round(prev_total_rev, 2), round(prev_total_cost, 2), round(prev_total_margin, 2), f"{prev_total_margin_pct:.2f}%"],
            })

            st.dataframe(summary_table, use_container_width=True, hide_index=True)

            # Save current month's snapshot
            if st.button("Save Monthly Snapshot", type="primary", key="save_snapshot_btn"):
                _save_monthly_snapshot(selected_year, current_month, sum_rev, sum_cost, sum_margin, sum_margin_pct)
                st.success(f"Snapshot saved for {selected_year}-{current_month:02d}. This will appear as Q1'-Q4' next month.")

        # Download Firm Revenue
        if not edited_rev.empty:
            output = BytesIO()
            rev_csv = edited_rev.to_csv(index=False)
            cost_csv = edited_cost.to_csv(index=False) if not edited_cost.empty else ""
            combined = "--- Revenue ---\n" + rev_csv + "\n--- Cost ---\n" + cost_csv
            st.download_button(
                label="Download Firm Revenue as CSV",
                data=combined,
                file_name=f"firm_revenue_{selected_year}.csv",
                mime="text/csv"
            )
