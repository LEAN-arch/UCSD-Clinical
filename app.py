import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime
import io
import time
import logging

from prophet import Prophet
from pptx import Presentation
from pptx.util import Inches, Pt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

# ======================================================================================
# SECTION 1: APP CONFIGURATION & STYLING
# ======================================================================================
st.set_page_config(
    page_title="MCC CTO | Scientific QA Command Center",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>
    .main .block-container { padding: 1rem 3rem 3rem; }
    .stMetric { background-color: #fcfcfc; border: 1px solid #e0e0e0; border-left: 5px solid #003b5c; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #F0F2F6; border-radius: 4px 4px 0px 0px; padding-top: 10px; padding-bottom: 10px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; box-shadow: 0 -2px 5px rgba(0,0,0,0.1); border-bottom-color: #FFFFFF !important; }
    .st-expander { border: 1px solid #E0E0E0 !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ======================================================================================
# SECTION 1.5: SUPPRESS VERBOSE LOGGING
# Silences informational messages from Prophet's backend (cmdstanpy) for a cleaner output.
# ======================================================================================
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)


# ======================================================================================
# SECTION 2: DATA SIMULATION & PRE-COMPUTATION
# ======================================================================================
@st.cache_data(ttl=900)
def generate_master_data():
    np.random.seed(42)
    num_trials = 60
    trial_ids = [f'MCC-{t}-{i:03d}' for t in ['IIT', 'IND', 'COG'] for i in range(1, 11)] + [f'INDUSTRY-{c}-{i:03d}' for c in ['PFE', 'BMY', 'MRK'] for i in range(1, 11)]
    portfolio_data = {'Trial_ID': trial_ids, 'Trial_Type': np.random.choice(['Investigator-Initiated (IIT)', 'Industry-Sponsored', 'Cooperative Group'], num_trials, p=[0.4, 0.4, 0.2]), 'Phase': np.random.choice(['I', 'I/II', 'II', 'III'], num_trials, p=[0.2, 0.3, 0.4, 0.1]), 'Disease_Team': np.random.choice(['Leukemia', 'Lung', 'Breast', 'GI', 'GU', 'Melanoma'], num_trials), 'Status': np.random.choice(['Enrolling', 'Follow-up', 'Closed to Accrual', 'Suspended'], num_trials, p=[0.6, 0.2, 0.15, 0.05]), 'Subjects_Enrolled': np.random.randint(5, 100, num_trials), 'PI_Experience_Level': np.random.choice(['Expert', 'Intermediate', 'New'], num_trials, p=[0.3, 0.5, 0.2]), 'Is_First_In_Human': np.random.choice([True, False], num_trials, p=[0.1, 0.9]), 'Num_Sites': np.random.choice([1, 2, 5], num_trials, p=[0.8, 0.15, 0.05])}
    portfolio_df = pd.DataFrame(portfolio_data)
    pis_by_team = {team: [f'Dr. {team_initials}{i}' for i in range(1,5)] for team, team_initials in zip(portfolio_df['Disease_Team'].unique(), ['L', 'U', 'B', 'GI', 'GU', 'M'])}
    portfolio_df['PI_Name'] = portfolio_df.apply(lambda row: np.random.choice(pis_by_team[row['Disease_Team']]), axis=1)
    finding_categories = ['Informed Consent Process', 'Source Data Verification', 'Investigational Product Accountability', 'Regulatory Binder Mgmt', 'AE/SAE Reporting', 'Protocol Adherence']
    findings_data = {'Finding_ID': [f'FIND-{i:04d}' for i in range(1, 251)], 'Trial_ID': np.random.choice(portfolio_df['Trial_ID'], 250), 'Category': np.random.choice(finding_categories, 250, p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1]), 'Risk_Level': np.random.choice(['Critical', 'Major', 'Minor'], 250, p=[0.05, 0.35, 0.6]), 'CAPA_Status': np.random.choice(['Open', 'Pending Verification', 'Closed-Effective', 'Overdue'], 250, p=[0.15, 0.1, 0.7, 0.05]), 'Finding_Date': pd.to_datetime([datetime.date(2022, 1, 1) + datetime.timedelta(days=int(d)) for d in np.random.randint(0, 700, 250)])}
    findings_df = pd.DataFrame(findings_data).merge(portfolio_df[['Trial_ID', 'Disease_Team', 'Trial_Type', 'PI_Name']], on='Trial_ID', how='left')
    major_finding_trials = findings_df[findings_df['Risk_Level'].isin(['Major', 'Critical'])]['Trial_ID'].unique()
    portfolio_df['Had_Major_Finding'] = portfolio_df['Trial_ID'].isin(major_finding_trials).astype(int)
    auditors = ['Jane Doe, RN', 'John Smith, PhD', 'Maria Garcia, MPH', 'Kevin Lee, CCRC']
    team_data = {'Auditor': auditors, 'Audits_Conducted_YTD': np.random.randint(15, 30, len(auditors)), 'Avg_Report_Turnaround_Days': np.random.uniform(8, 20, len(auditors)), 'GCP_Certification_Status': np.random.choice(['Current', 'Expires <90d'], len(auditors), p=[0.75, 0.25]), 'IIT_Oversight_Skill': np.random.randint(3, 6, len(auditors)), 'FDA_Inspection_Mgmt_Skill': np.random.randint(2, 5, len(auditors))}
    team_df = pd.DataFrame(team_data)
    initiatives_data = {'Initiative': ['eQMS Implementation', 'Auditor Training Program Revamp', 'Inspection Readiness Mock Audits', 'IIT Risk-Based Monitoring Plan'], 'Lead': ['Jane Doe, RN', 'John Smith, PhD', 'Maria Garcia, MPH', 'Kevin Lee, CCRC'], 'Status': ['On Track', 'At Risk', 'Completed', 'On Track'], 'Percent_Complete': [60, 85, 100, 30], 'Start_Date': pd.to_datetime(['2023-01-15', '2023-03-01', '2023-06-01', '2023-09-01']), 'End_Date': pd.to_datetime(['2024-06-30', '2023-11-30', '2023-08-31', '2024-03-31']), 'Budget_USD': [75000, 15000, 25000, 10000], 'Spent_USD': [40000, 14000, 23500, 2500]}
    initiatives_df = pd.DataFrame(initiatives_data)
    return portfolio_df, findings_df, team_df, initiatives_df

# ======================================================================================
# SECTION 3: ANALYTICAL & REPORTING MODELS
# ======================================================================================
@st.cache_resource
def get_trial_risk_model(portfolio_df):
    features, target = ['Trial_Type', 'Phase', 'PI_Experience_Level', 'Is_First_In_Human', 'Num_Sites'], 'Had_Major_Finding'
    X, y = portfolio_df[features], portfolio_df[target]
    categorical_features = ['Trial_Type', 'Phase', 'PI_Experience_Level']
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    X_encoded = pd.DataFrame(encoder.fit_transform(X[categorical_features]), columns=encoder.get_feature_names_out(categorical_features))
    X_final = pd.concat([X.drop(columns=categorical_features).reset_index(drop=True), X_encoded], axis=1)
    model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    model.fit(X_final, y)
    return model, encoder, X_final.columns

def plot_spc_chart(df, date_col, category_col, value, title):
    df_filtered = df[df[category_col] == value].copy()
    df_filtered = df_filtered.set_index(date_col).sort_index()
    monthly_counts = df_filtered.resample('ME').size().reset_index(name='findings')
    monthly_counts['month'] = monthly_counts[date_col].dt.to_period('M')
    if monthly_counts.empty or monthly_counts['findings'].sum() == 0: return go.Figure().update_layout(title=f'<b>{title}</b><br>No data available for this category.')
    p_bar, std_dev = monthly_counts['findings'].mean(), np.sqrt(monthly_counts['findings'].mean())
    UCL, LCL = p_bar + 3 * std_dev, max(0, p_bar - 3 * std_dev)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_counts['month'].astype(str), y=monthly_counts['findings'], mode='lines+markers', name='Monthly Findings', line=dict(color='#003b5c')))
    fig.add_hline(y=p_bar, line_dash="dot", line_color="green", name='Center Line (Mean)')
    fig.add_hline(y=UCL, line_dash="dash", line_color="red", name='Upper Control Limit')
    fig.add_hline(y=LCL, line_dash="dash", line_color="red", name='Lower Control Limit')
    out_of_control = monthly_counts[monthly_counts['findings'] > UCL]
    fig.add_trace(go.Scatter(x=out_of_control['month'].astype(str), y=out_of_control['findings'], mode='markers', name='Out of Control', marker=dict(color='red', size=12, symbol='x')))
    fig.update_layout(title=f'<b>{title}</b>', xaxis_title='Month', yaxis_title='Number of Findings', plot_bgcolor='white', height=400)
    return fig

@st.cache_data(ttl=3600)
def generate_prophet_forecast(findings_df):
    df_prophet = findings_df[['Finding_Date']].copy(); df_prophet['y'] = 1; df_prophet = df_prophet.rename(columns={'Finding_Date': 'ds'})
    monthly_df = df_prophet.set_index('ds').resample('ME').count().reset_index()
    model = Prophet(yearly_seasonality=True, daily_seasonality=False); model.fit(monthly_df)
    future = model.make_future_dataframe(periods=12, freq='ME'); forecast = model.predict(future)
    return forecast, monthly_df

def plot_prophet_forecast(forecast, monthly_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_df['ds'], y=monthly_df['y'], mode='markers', name='Actual Findings'))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Forecast', line=dict(color='#003b5c')))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], fill=None, mode='lines', line_color='rgba(0,59,92,0.2)', name='Upper Bound'))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], fill='tonexty', mode='lines', line_color='rgba(0,59,92,0.2)', name='Lower Bound'))
    fig.update_layout(title='<b>12-Month Forecast of Total Audit Findings</b>', xaxis_title='Date', yaxis_title='Number of Findings', plot_bgcolor='white')
    return fig

def plot_findings_heatmap_by_team(df):
    heatmap_data = pd.crosstab(df['Disease_Team'], df['Category'])
    fig = px.imshow(heatmap_data, labels=dict(x="Finding Category", y="Disease Team", color="Number of Findings"), color_continuous_scale=px.colors.sequential.Blues, title="<b>Heatmap of Finding Categories by Disease Team</b>")
    fig.update_layout(height=450)
    return fig

def generate_ppt_report(kpi_data, spc_fig, findings_table_df):
    prs = Presentation(); prs.slide_width = Inches(16); prs.slide_height = Inches(9)
    title_slide_layout = prs.slide_layouts[0]; slide = prs.slides.add_slide(title_slide_layout); slide.shapes.title.text = "MCC CTO Quality Assurance Executive Summary"; slide.placeholders[1].text = f"Report Generated: {datetime.date.today().strftime('%Y-%m-%d')}"
    kpi_slide_layout = prs.slide_layouts[5]; slide = prs.slides.add_slide(kpi_slide_layout); slide.shapes.title.text = "QA Program Health Dashboard"
    positions = [(Inches(1), Inches(1.5)), (Inches(5), Inches(1.5)), (Inches(9), Inches(1.5)), (Inches(13), Inches(1.5))]
    for i, (kpi_title, kpi_val, kpi_delta) in enumerate(kpi_data):
        txBox = slide.shapes.add_textbox(positions[i][0], positions[i][1], Inches(3.5), Inches(2)); tf = txBox.text_frame; tf.word_wrap = True
        p1 = tf.paragraphs[0]; p1.text = kpi_title; p1.font.bold = True; p1.font.size = Pt(20)
        p2 = tf.add_paragraph(); p2.text = str(kpi_val); p2.font.size = Pt(44); p2.font.bold = True
        p3 = tf.add_paragraph(); p3.text = str(kpi_delta); p3.font.size = Pt(16)
    content_slide_layout = prs.slide_layouts[5]; slide = prs.slides.add_slide(content_slide_layout); slide.shapes.title.text = "Systemic Process Control (SPC) Analysis"
    image_stream = io.BytesIO(); spc_fig.write_image(image_stream, format='png', scale=2); image_stream.seek(0); slide.shapes.add_picture(image_stream, Inches(1), Inches(1.5), width=Inches(14))
    table_slide_layout = prs.slide_layouts[5]; slide = prs.slides.add_slide(table_slide_layout); slide.shapes.title.text = "High-Priority Open Findings (Critical/Major)"
    rows, cols = findings_table_df.shape[0] + 1, findings_table_df.shape[1]; table = slide.shapes.add_table(rows, cols, Inches(1), Inches(1.5), Inches(14), Inches(0.5) * rows).table
    for col_idx, col_name in enumerate(findings_table_df.columns): table.cell(0, col_idx).text = col_name
    for ppt_row_idx, df_row in enumerate(findings_table_df.itertuples(index=False), start=1):
        for col_idx, cell_data in enumerate(df_row): table.cell(ppt_row_idx, col_idx).text = str(cell_data)
    ppt_stream = io.BytesIO(); prs.save(ppt_stream); ppt_stream.seek(0)
    return ppt_stream

# ======================================================================================
# SECTION 4: MAIN APPLICATION LAYOUT & LOGIC
# ======================================================================================
st.title("🔬 MCC CTO Scientific QA Command Center")
st.markdown("##### An advanced analytics dashboard for strategic quality oversight, forecasting, and reporting.")

# --- Data Loading and Prep ---
portfolio_df, findings_df, team_df, initiatives_df = generate_master_data()
risk_model, encoder, model_features = get_trial_risk_model(portfolio_df)
forecast_data, actual_monthly_data = generate_prophet_forecast(findings_df)
findings_df['Finding_Date'] = pd.to_datetime(findings_df['Finding_Date'])
findings_df['Closure_Date'] = findings_df.apply(lambda row: row['Finding_Date'] + pd.to_timedelta(np.random.randint(5, 60), unit='d') if row['CAPA_Status'] == 'Closed-Effective' else pd.NaT, axis=1)
findings_df['Days_to_Close'] = (findings_df['Closure_Date'] - findings_df['Finding_Date']).dt.days

# --- Executive Dashboard ---
st.markdown("### I. Executive QA Program Health Dashboard")
kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
risk_weights = {'Critical': 10, 'Major': 5, 'Minor': 1}
open_findings = findings_df[~findings_df['CAPA_Status'].isin(['Closed-Effective'])].copy()
open_findings['Risk_Score'] = open_findings['Risk_Level'].map(risk_weights)
total_risk_score = int(open_findings['Risk_Score'].sum())
overdue_major_capas = findings_df[(findings_df['CAPA_Status'] == 'Overdue') & (findings_df['Risk_Level'] != 'Minor')].shape[0]
readiness_score = max(0, 100 - (overdue_major_capas * 10) - (open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0] * 5))
team_df['Strain'] = (team_df['Audits_Conducted_YTD'] * team_df['Avg_Report_Turnaround_Days']) / 100
avg_strain = team_df['Strain'].mean()

kpi_col1.metric("Portfolio-wide Risk Score", f"{total_risk_score}", f"{open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0]} Open Criticals", "inverse")
kpi_col2.metric("Inspection Readiness Index", f"{readiness_score}%", f"{overdue_major_capas} Overdue Major CAPAs", "inverse")
kpi_col3.metric("Avg. Resource Strain Index", f"{avg_strain:.2f}", "Target < 4.0", "normal")
st.markdown("---")

# --- Main Application Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["**II. PREDICTIVE ANALYTICS**", "**III. SYSTEMIC RISK ANALYSIS**", "**IV. PI PERFORMANCE OVERSIGHT**", "**V. ORGANIZATIONAL CAPABILITY**"])

with tab1:
    st.header("II. Predictive Analytics & Forecasting")
    st.markdown("_This section utilizes predictive modeling to forecast future states and quantify inherent risk, enabling a proactive, data-driven approach to quality management._")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("A. Time-Series Forecast of Audit Finding Volume")
        with st.expander("View Methodological Summary"):
            st.markdown("- **Purpose:** To forecast future operational workload.\n- **Method:** An additive time-series model (`Prophet`) projects volumes for the next 12 months.\n- **Interpretation:** An upward trend may signal a need for more resources.")
        st.plotly_chart(plot_prophet_forecast(forecast_data, actual_monthly_data), use_container_width=True)
    with col2:
        st.subheader("B. Inherent Risk Prediction for New Trials")
        with st.expander("View Methodological Summary"):
            st.markdown("- **Purpose:** To quantify a priori trial risk, aligning with RBQM.\n- **Method:** A logistic regression model predicts the probability of a major finding.\n- **Interpretation:** The score allows for triaging new protocols into risk tiers, optimizing resource allocation.")
        p_type = st.selectbox("Trial Type", portfolio_df['Trial_Type'].unique(), key='p_type')
        p_phase = st.selectbox("Trial Phase", portfolio_df['Phase'].unique(), key='p_phase')
        p_pi_exp = st.selectbox("PI Experience", portfolio_df['PI_Experience_Level'].unique(), key='p_pi')
        if st.button("🔬 Forecast Risk Profile", type="primary"):
            input_df = pd.DataFrame({'Trial_Type': [p_type], 'Phase': [p_phase], 'PI_Experience_Level': [p_pi_exp], 'Is_First_In_Human': [False], 'Num_Sites': [1]})
            input_encoded = pd.DataFrame(encoder.transform(input_df[['Trial_Type', 'Phase', 'PI_Experience_Level']]), columns=encoder.get_feature_names_out(['Trial_Type', 'Phase', 'PI_Experience_Level']))
            input_final = pd.concat([input_df.drop(columns=['Trial_Type', 'Phase', 'PI_Experience_Level']).reset_index(drop=True), input_encoded], axis=1).reindex(columns=model_features, fill_value=0)
            prediction_proba = risk_model.predict_proba(input_final)[0][1]
            st.success(f"Predicted Risk of Major Finding: **{prediction_proba:.1%}**")

with tab2:
    st.header("III. Systemic Process & Risk Analysis")
    st.markdown("_This section moves beyond individual data points to identify systemic trends, process vulnerabilities, and non-random patterns across the clinical trial portfolio._")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("A. Statistical Process Control (SPC) Analysis")
        with st.expander("View Methodological Summary"):
            st.markdown("- **Purpose:** To distinguish between random variation and significant deviations.\n- **Method:** A Shewhart c-chart with 3-sigma control limits.\n- **Interpretation:** A point outside the limits (red 'X') requires Root Cause Analysis (RCA).")
        category_to_monitor = st.selectbox("Select Finding Category to Analyze for Trends:", options=findings_df['Category'].unique())
        st.plotly_chart(plot_spc_chart(findings_df, 'Finding_Date', 'Category', category_to_monitor, f"SPC c-Chart for '{category_to_monitor}' Findings"), use_container_width=True)
    with col2:
        st.subheader("B. Finding Concentration Analysis by Disease Team")
        with st.expander("View Methodological Summary"):
            st.markdown("- **Purpose:** To identify non-random associations between Teams and finding types.\n- **Method:** A heatmap of finding counts.\n- **Interpretation:** 'Hot spots' suggest localized process gaps, enabling targeted interventions.")
        st.plotly_chart(plot_findings_heatmap_by_team(findings_df), use_container_width=True)

    st.markdown("---")
    st.subheader("C. Interactive Regulatory Inspection Simulation")
    with st.expander("View Methodological Summary"):
        st.markdown("- **Purpose:** To pressure-test operational readiness for a 'live fire' inspection.\n- **Method:** A mock eTMF retrieval system.\n- **Interpretation:** Transforms 'readiness' from an abstract concept into a tangible, measurable capability.")
    @st.cache_data
    def create_mock_etmf(portfolio_df):
        mock_etmf = {}
        for _, row in portfolio_df.iterrows():
            trial_id, num_subjects = row['Trial_ID'], row['Subjects_Enrolled']
            mock_etmf[trial_id] = {"Protocol Signature Page": f"DocRef_PSP_{trial_id}.pdf", "IRB Approval Letter": f"DocRef_IRB_Approval_{trial_id}.pdf", "FDA Form 1572": f"DocRef_1572_{trial_id}.pdf" if "IIT" in trial_id or "IND" in trial_id else "N/A", "Informed Consent Forms": {f"Subject-{i:03d}": f"ICF_{trial_id}_Subj_{i:03d}.pdf" for i in range(1, num_subjects + 1)}, "Serious Adverse Event Reports": {f"SAE-{i:03d}": f"SAE_{trial_id}_{i:03d}.pdf" for i in range(1, np.random.randint(2, 6))}}
        return mock_etmf
    mock_etmf_db = create_mock_etmf(portfolio_df)
    sim_col1, sim_col2 = st.columns([1, 2])
    with sim_col1:
        st.write("**Inspection Scenario:**")
        trial_to_inspect = st.selectbox("Select a Trial to Inspect:", options=portfolio_df['Trial_ID'], key="inspect_trial")
        subject_list = list(mock_etmf_db[trial_to_inspect]["Informed Consent Forms"].keys())
        if subject_list:
            subject_to_inspect = st.selectbox("Select a Subject:", options=subject_list, key="inspect_subject")
        else:
            subject_to_inspect = None

    if subject_to_inspect and st.button("🔬 Pull Subject's Consent Form"):
        with sim_col2:
            st.info(f"Request: 'Please provide the signed consent form for {subject_to_inspect} on trial {trial_to_inspect}.'")
            with st.spinner("Searching eTMF..."): time.sleep(1.5)
            st.success("**Document Found!**"); st.code(f"File Path: /eTMF/Trials/{trial_to_inspect}/Subject_Files/{subject_to_inspect}/ICF_{trial_to_inspect}_Subj_{subject_to_inspect.split('-')[1]}.pdf\nAccessed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", language="bash")
    if st.button("📄 Pull Trial's 1572 Form"):
        with sim_col2:
            st.info(f"Request: 'Please provide the current FDA Form 1572 for trial {trial_to_inspect}.'")
            with st.spinner("Searching eTMF..."): time.sleep(1)
            doc_ref = mock_etmf_db[trial_to_inspect].get("FDA Form 1572")
            if doc_ref != "N/A": st.success("**Document Found!**"); st.code(f"File Path: /eTMF/Trials/{trial_to_inspect}/Regulatory/{doc_ref}\nAccessed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", language="bash")
            else: st.error("**Document Not Applicable!** This is not an IND-holding trial.")

with tab3:
    st.header("IV. Principal Investigator (PI) Performance Oversight")
    st.markdown("_This section enables granular analysis of quality metrics at the individual PI level, benchmarked against their Disease Team peers. It is a tool for targeted coaching and support._")
    pi_col1, pi_col2 = st.columns(2)
    with pi_col1:
        selected_team = st.selectbox("Select a Disease Team to Analyze:", options=sorted(portfolio_df['Disease_Team'].unique()), key="team_select")
        available_pis = sorted(portfolio_df[portfolio_df['Disease_Team'] == selected_team]['PI_Name'].unique())
        selected_pi = st.selectbox("Select a Principal Investigator:", options=available_pis, key="pi_select")
    pi_findings = findings_df[findings_df['PI_Name'] == selected_pi]
    team_findings = findings_df[findings_df['Disease_Team'] == selected_team]
    with pi_col2:
        st.subheader(f"Performance Snapshot: {selected_pi}")
        m_col1, m_col2, m_col3 = st.columns(3)
        pi_major_findings = pi_findings[pi_findings['Risk_Level'].isin(['Major', 'Critical'])].shape[0]
        team_avg_major_findings = team_findings[team_findings['Risk_Level'].isin(['Major', 'Critical'])].groupby('PI_Name').size().mean()
        m_col1.metric("Major/Critical Findings", f"{pi_major_findings}", f"Team Avg: {team_avg_major_findings:.1f}", delta_color="inverse")
        pi_avg_closure, team_avg_closure = pi_findings['Days_to_Close'].mean(), team_findings['Days_to_Close'].mean()
        m_col2.metric("Avg. CAPA Closure (Days)", f"{pi_avg_closure:.1f}" if not np.isnan(pi_avg_closure) else "N/A", f"Team Avg: {team_avg_closure:.1f}", delta_color="inverse")
        pi_overdue = pi_findings[pi_findings['CAPA_Status'] == 'Overdue'].shape[0]
        team_avg_overdue = team_findings.groupby('PI_Name')['CAPA_Status'].apply(lambda x: (x == 'Overdue').sum()).mean()
        m_col3.metric("Overdue CAPAs", f"{pi_overdue}", f"Team Avg: {team_avg_overdue:.1f}", delta_color="inverse")
    st.markdown("---")
    st.subheader(f"Findings Breakdown for {selected_pi}")
    if pi_findings.empty:
        st.warning(f"No findings recorded for {selected_pi}.")
    else:
        st.plotly_chart(px.pie(pi_findings, names='Category', title='Finding Categories', hole=0.3), use_container_width=True)

with tab4:
    st.header("V. Organizational Capability & Strategic Oversight")
    st.markdown("_This section assesses the capacity of the QA team and tracks progress and financial health of key strategic objectives._")
    st.subheader("A. Auditor Workload & Performance Analysis")
    with st.expander("View Methodological Summary"):
        st.markdown("- **Purpose:** To manage human capital risk by visualizing workload vs. efficiency.\n- **Method:** A scatter plot of Audits Conducted vs. Report Turnaround Time with a composite 'Strain Index'.\n- **Interpretation:** Identifies archetypes for targeted management (e.g., high-strain vs. high-efficiency).")
    fig = px.scatter(team_df, x='Audits_Conducted_YTD', y='Avg_Report_Turnaround_Days', size='Strain', color='Strain', text='Auditor', title='<b>QA Team Resource & Strain Analysis</b>', labels={'Audits_Conducted_YTD': 'Audits Conducted (Workload)', 'Avg_Report_Turnaround_Days': 'Avg. Report Turnaround (Efficiency)'}, color_continuous_scale=px.colors.sequential.OrRd)
    fig.update_traces(textposition='top center'); fig.add_hline(y=team_df['Avg_Report_Turnaround_Days'].mean(), line_dash="dot"); fig.add_vline(x=team_df['Audits_Conducted_YTD'].mean(), line_dash="dot")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("B. Strategic Initiatives & Financial Oversight")
    st.markdown("This table tracks financial health and schedule adherence for key projects, projecting final costs and identifying potential overruns.")
    today = pd.to_datetime(datetime.date.today())
    initiatives_df['Days_Elapsed'] = (today - initiatives_df['Start_Date']).dt.days
    initiatives_df['Total_Days_Planned'] = (initiatives_df['End_Date'] - initiatives_df['Start_Date']).dt.days
    initiatives_df['Daily_Burn_Rate'] = initiatives_df.apply(lambda row: row['Spent_USD'] / row['Days_Elapsed'] if row['Days_Elapsed'] > 0 else 0, axis=1)
    initiatives_df['Projected_Total_Cost'] = initiatives_df['Daily_Burn_Rate'] * initiatives_df['Total_Days_Planned']
    initiatives_df['Projected_Over_Under'] = initiatives_df['Budget_USD'] - initiatives_df['Projected_Total_Cost']
    initiatives_df['CPI'] = initiatives_df.apply(lambda row: (row['Budget_USD'] * row['Percent_Complete']/100) / row['Spent_USD'] if row['Spent_USD'] > 0 else 0, axis=1)
    initiatives_df['SPI'] = initiatives_df.apply(lambda row: (row['Percent_Complete']/100) / (row['Days_Elapsed']/row['Total_Days_Planned']) if row['Days_Elapsed'] > 0 and row['Total_Days_Planned'] > 0 else 0, axis=1)
    def format_financials(df):
        return df.style.format({'Budget_USD': "${:,.0f}", 'Spent_USD': "${:,.0f}", 'Projected_Total_Cost': "${:,.0f}", 'Projected_Over_Under': "${:,.0f}", 'Daily_Burn_Rate': "${:,.2f}", 'CPI': "{:.2f}", 'SPI': "{:.2f}"}).background_gradient(cmap='RdYlGn', subset=['Projected_Over_Under']).background_gradient(cmap='RdYlGn', vmin=0.8, vmax=1.2, subset=['CPI', 'SPI']).bar(subset=['Percent_Complete'], color='#5cadff', vmin=0, vmax=100)
    st.dataframe(format_financials(initiatives_df[['Initiative', 'Lead', 'Status', 'Percent_Complete', 'Budget_USD', 'Spent_USD', 'Projected_Total_Cost', 'Projected_Over_Under', 'CPI', 'SPI']]), use_container_width=True)
    st.caption("CPI (Cost Performance Index): > 1.0 is favorable. SPI (Schedule Performance Index): > 1.0 is favorable.")

# ======================================================================================
# SECTION 5: SIDEBAR & AUTOMATED EXECUTIVE REPORTING
# ======================================================================================
st.sidebar.markdown("## Moores Cancer Center")
st.sidebar.markdown("### Clinical Trials Office")
st.sidebar.markdown("---")
st.sidebar.markdown("### About this Dashboard")
st.sidebar.info("This **Scientific QA Command Center** leverages advanced analytics to empower the Assistant Director of QA. It is designed to facilitate proactive risk management, data-driven resource allocation, and a state of continuous inspection readiness.")
st.sidebar.markdown("---")
st.sidebar.header("Generate Executive Report")
st.sidebar.info("Click to download a PowerPoint summary of the current QA program status for leadership review.")
kpi_data_for_report = [("Portfolio Risk Score", total_risk_score, f"{open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0]} Open Criticals"), ("Inspection Readiness", f"{readiness_score}%", f"{overdue_major_capas} Overdue Major CAPAs"), ("Resource Strain Index", f"{avg_strain:.2f}", "Target < 4.0")]
findings_for_report = findings_df[(findings_df['Risk_Level'].isin(['Major', 'Critical'])) & (findings_df['CAPA_Status'] != 'Closed-Effective')][['Trial_ID', 'Category', 'Risk_Level', 'CAPA_Status']].head(10)
default_spc_fig = plot_spc_chart(findings_df, 'Finding_Date', 'Category', 'Informed Consent Process', "SPC Chart: Informed Consent Findings")
with st.sidebar, st.spinner("Generating PowerPoint report..."):
    ppt_buffer = generate_ppt_report(kpi_data_for_report, default_spc_fig, findings_for_report)
    st.download_button(label="📥 Download PowerPoint Report", data=ppt_buffer, file_name=f"MCC_CTO_QA_Summary_{datetime.date.today()}.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

st.sidebar.markdown("---")
st.sidebar.markdown("### Key Concepts & Regulations")
st.sidebar.markdown("- **RBQM:** Risk-Based Quality Management (ICH E6)\n- **SPC:** Statistical Process Control\n- **CPI/SPI:** Cost/Schedule Performance Index\n- **GCP:** Good Clinical Practice (ICH E6)\n- **21 CFR Part 50:** Protection of Human Subjects (Informed Consent)\n- **21 CFR Part 312:** Investigational New Drug Application\n- **CAPA:** Corrective and Preventive Action")
