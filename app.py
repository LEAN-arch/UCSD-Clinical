# ======================================================================================
# MCC CTO QA COMMAND CENTER: FORECASTING & REPORTING EDITION
#
# A single-file Streamlit application for the Assistant Director, Quality Assurance,
# Moores Cancer Center (MCC) Clinical Trials Office (CTO).
#
# VERSION: Final (Forecasting, Reporting, and Complete Acronyms)
#
# This dashboard provides a proactive, intelligent, and risk-based view of the
# CTO's QA Program. It now includes time-series forecasting to predict future
# workload and a one-click PowerPoint report generator for executive briefings.
# It is built upon principles from:
#   - Good Clinical Practice (GCP) - ICH E6 (R2)
#   - US FDA Regulations (21 CFR Parts 11, 50, 56, 312)
#   - NCI Guidelines & Cancer Center Support Grant (CCSG) requirements
#   - Quality by Design (QbD) and Risk-Based Quality Management (RBQM)
#
# To Run:
# 1. Save this code as 'mcc_cto_final_dashboard.py'
# 2. Create 'requirements.txt' with the specified libraries.
# 3. Install dependencies: pip install -r requirements.txt
# 4. Run from your terminal: streamlit run mcc_cto_final_dashboard.py
#
# ======================================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime
import io

# --- INTEGRATION: Import newly required libraries ---
from prophet import Prophet
from pptx import Presentation
from pptx.util import Inches, Pt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
# Kaleido is used by plotly's `to_image` method, no direct import needed.

# ======================================================================================
# SECTION 1: APP CONFIGURATION & STYLING
# ======================================================================================
st.set_page_config(
    page_title="MCC CTO | Predictive QA Command Center",
    page_icon="🧬",
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
</style>
""", unsafe_allow_html=True)


# ======================================================================================
# SECTION 2: DATA SIMULATION
# ======================================================================================
@st.cache_data(ttl=900)
def generate_master_data():
    """Simulates a comprehensive, interconnected dataset for a realistic oncology CTO."""
    np.random.seed(42)
    num_trials = 60
    trial_ids = [f'MCC-{t}-{i:03d}' for t in ['IIT', 'IND', 'COG'] for i in range(1, 11)] + \
                [f'INDUSTRY-{c}-{i:03d}' for c in ['PFE', 'BMY', 'MRK'] for i in range(1, 11)]

    portfolio_data = {
        'Trial_ID': trial_ids,
        'Trial_Type': np.random.choice(['Investigator-Initiated (IIT)', 'Industry-Sponsored', 'Cooperative Group'], num_trials, p=[0.4, 0.4, 0.2]),
        'Phase': np.random.choice(['I', 'I/II', 'II', 'III'], num_trials, p=[0.2, 0.3, 0.4, 0.1]),
        'Disease_Team': np.random.choice(['Leukemia', 'Lung', 'Breast', 'GI', 'GU', 'Melanoma'], num_trials),
        'Status': np.random.choice(['Enrolling', 'Follow-up', 'Closed to Accrual', 'Suspended'], num_trials, p=[0.6, 0.2, 0.15, 0.05]),
        'Subjects_Enrolled': np.random.randint(5, 100, num_trials),
        'PI_Experience_Level': np.random.choice(['Expert', 'Intermediate', 'New'], num_trials, p=[0.3, 0.5, 0.2]),
        'Is_First_In_Human': np.random.choice([True, False], num_trials, p=[0.1, 0.9]),
        'Num_Sites': np.random.choice([1, 2, 5], num_trials, p=[0.8, 0.15, 0.05])
    }
    portfolio_df = pd.DataFrame(portfolio_data)

    num_findings = 250
    finding_categories = ['Informed Consent Process', 'Source Data Verification', 'Investigational Product Accountability', 'Regulatory Binder Mgmt', 'AE/SAE Reporting', 'Protocol Adherence']
    findings_data = {
        'Finding_ID': [f'FIND-{i:04d}' for i in range(1, num_findings + 1)],
        'Trial_ID': np.random.choice(portfolio_df['Trial_ID'], num_findings),
        'Category': np.random.choice(finding_categories, num_findings, p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1]),
        'Risk_Level': np.random.choice(['Critical', 'Major', 'Minor'], num_findings, p=[0.05, 0.35, 0.6]),
        'CAPA_Status': np.random.choice(['Open', 'Pending Verification', 'Closed-Effective', 'Overdue'], num_findings, p=[0.15, 0.1, 0.7, 0.05]),
        'Finding_Date': pd.to_datetime([datetime.date(2022, 1, 1) + datetime.timedelta(days=int(d)) for d in np.random.randint(0, 700, num_findings)]),
    }
    findings_df = pd.DataFrame(findings_data).merge(portfolio_df[['Trial_ID', 'Disease_Team', 'Trial_Type']], on='Trial_ID', how='left')
    
    major_finding_trials = findings_df[findings_df['Risk_Level'].isin(['Major', 'Critical'])]['Trial_ID'].unique()
    portfolio_df['Had_Major_Finding'] = portfolio_df['Trial_ID'].isin(major_finding_trials).astype(int)

    auditors = ['Jane Doe, RN', 'John Smith, PhD', 'Maria Garcia, MPH', 'Kevin Lee, CCRC']
    team_data = { 'Auditor': auditors, 'Audits_Conducted_YTD': np.random.randint(15, 30, len(auditors)), 'Avg_Report_Turnaround_Days': np.random.uniform(8, 20, len(auditors)), 'GCP_Certification_Status': np.random.choice(['Current', 'Expires <90d'], len(auditors), p=[0.75, 0.25]), 'IIT_Oversight_Skill': np.random.randint(3, 6, len(auditors)), 'FDA_Inspection_Mgmt_Skill': np.random.randint(2, 5, len(auditors)), }
    team_df = pd.DataFrame(team_data)
    
    initiatives_data = { 'Initiative': ['eQMS Implementation', 'Auditor Training Program Revamp', 'Inspection Readiness Mock Audits', 'IIT Risk-Based Monitoring Plan'], 'Lead': ['Jane Doe, RN', 'John Smith, PhD', 'Maria Garcia, MPH', 'Kevin Lee, CCRC'], 'Status': ['On Track', 'At Risk', 'Completed', 'On Track'], 'Percent_Complete': [60, 85, 100, 30], 'Budget_USD': [75000, 15000, 25000, 10000], 'Spent_USD': [40000, 14000, 23500, 2500] }
    initiatives_df = pd.DataFrame(initiatives_data)

    return portfolio_df, findings_df, team_df, initiatives_df

# ======================================================================================
# SECTION 3: PREDICTIVE MODELS & PLOTTING FUNCTIONS
# ======================================================================================
@st.cache_resource
def get_trial_risk_model(portfolio_df):
    features = ['Trial_Type', 'Phase', 'PI_Experience_Level', 'Is_First_In_Human', 'Num_Sites']
    target = 'Had_Major_Finding'
    X = portfolio_df[features]
    y = portfolio_df[target]
    categorical_features = ['Trial_Type', 'Phase', 'PI_Experience_Level']
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    X_encoded = pd.DataFrame(encoder.fit_transform(X[categorical_features]), columns=encoder.get_feature_names_out(categorical_features))
    X_final = pd.concat([X.drop(columns=categorical_features).reset_index(drop=True), X_encoded], axis=1)
    model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    model.fit(X_final, y)
    importance_df = pd.DataFrame({'feature': X_final.columns, 'importance': model.coef_[0]}).sort_values(by='importance', key=abs, ascending=False)
    return model, encoder, X_final.columns, importance_df

def plot_spc_chart(df, date_col, category_col, value, title):
    df_filtered = df[df[category_col] == value].copy()
    df_filtered = df_filtered.set_index(date_col).sort_index()
    monthly_counts = df_filtered.resample('M').size().reset_index(name='findings')
    monthly_counts['month'] = monthly_counts[date_col].dt.to_period('M')
    p_bar = monthly_counts['findings'].mean()
    UCL = p_bar + 3 * np.sqrt(p_bar * (1 - p_bar) / monthly_counts['findings'].size if monthly_counts['findings'].size > 0 else 1)
    LCL = max(0, p_bar - 3 * np.sqrt(p_bar * (1 - p_bar) / monthly_counts['findings'].size if monthly_counts['findings'].size > 0 else 1))
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
def generate_prophet_forecast_plot(findings_df):
    df_prophet = findings_df[['Finding_Date']].copy()
    df_prophet['y'] = 1
    df_prophet = df_prophet.rename(columns={'Finding_Date': 'ds'})
    monthly_df = df_prophet.set_index('ds').resample('M').count().reset_index()
    model = Prophet(yearly_seasonality=True, daily_seasonality=False)
    model.fit(monthly_df)
    future = model.make_future_dataframe(periods=12, freq='M')
    forecast = model.predict(future)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_df['ds'], y=monthly_df['y'], mode='markers', name='Actual Findings'))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Forecast', line=dict(color='#003b5c')))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], fill=None, mode='lines', line_color='rgba(0,59,92,0.2)', name='Upper Bound'))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], fill='tonexty', mode='lines', line_color='rgba(0,59,92,0.2)', name='Lower Bound'))
    fig.update_layout(title='<b>12-Month Forecast of Total Audit Findings</b>', xaxis_title='Date', yaxis_title='Number of Findings', plot_bgcolor='white')
    return fig

def plot_findings_heatmap_by_team(df):
    heatmap_data = pd.crosstab(df['Disease_Team'], df['Category'])
    fig = px.imshow(heatmap_data, labels=dict(x="Finding Category", y="Disease Team", color="Number of Findings"),
                    x=heatmap_data.columns, y=heatmap_data.index, color_continuous_scale=px.colors.sequential.Blues,
                    title="<b>Heatmap of Finding Categories by Disease Team</b>")
    fig.update_layout(height=450)
    return fig

def plot_risk_gauge(probability, title):
    if probability > 0.6: color, level = "#d62728", "High Risk"
    elif probability > 0.3: color, level = "#ff7f0e", "Medium Risk"
    else: color, level = "#2ca02c", "Low Risk"
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = probability * 100,
        title = {'text': f"{title}<br><span style='font-size:0.8em;color:gray;'>{level}</span>", 'align': 'center'},
        gauge = {'axis': {'range': [None, 100], 'tickformat': '.0f', 'ticksuffix': '%'},
                 'bar': {'color': color}, 'steps': [{'range': [0, 30], 'color': '#eafaf1'}, {'range': [30, 60], 'color': '#fef5e7'}],
                 'threshold': {'line': {'color': "#d62728", 'width': 4}, 'thickness': 0.75, 'value': 60}}))
    fig.update_layout(height=250, margin=dict(t=80, b=20, l=30, r=30))
    return fig

# ======================================================================================
# SECTION 4: POWERPOINT REPORT GENERATOR
# ======================================================================================
def generate_ppt_report(kpi_data, spc_fig, findings_table_df):
    prs = Presentation()
    prs.slide_width = Inches(16)
    prs.slide_height = Inches(9)
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "MCC CTO Quality Assurance Executive Summary"
    subtitle.text = f"Report Generated: {datetime.date.today().strftime('%Y-%m-%d')}"
    kpi_slide_layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(kpi_slide_layout)
    title = slide.shapes.title
    title.text = "QA Program Health Dashboard"
    positions = [(Inches(1), Inches(1.5)), (Inches(5), Inches(1.5)), (Inches(9), Inches(1.5)), (Inches(13), Inches(1.5))]
    for i, (kpi_title, kpi_val, kpi_delta) in enumerate(kpi_data):
        txBox = slide.shapes.add_textbox(positions[i][0], positions[i][1], Inches(3.5), Inches(2))
        tf = txBox.text_frame
        p = tf.add_paragraph(); p.text = kpi_title; p.font.bold = True; p.font.size = Pt(20)
        p = tf.add_paragraph(); p.text = str(kpi_val); p.font.size = Pt(44); p.font.bold = True
        p = tf.add_paragraph(); p.text = str(kpi_delta); p.font.size = Pt(16)
    content_slide_layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(content_slide_layout)
    title = slide.shapes.title
    title.text = "Systemic Process Control (SPC) Analysis"
    image_stream = io.BytesIO()
    spc_fig.write_image(image_stream, format='png', scale=2)
    image_stream.seek(0)
    slide.shapes.add_picture(image_stream, Inches(1), Inches(1.5), width=Inches(14))
    table_slide_layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(table_slide_layout)
    title = slide.shapes.title
    title.text = "High-Priority Open Findings (Critical/Major)"
    rows, cols = findings_table_df.shape[0] + 1, findings_table_df.shape[1]
    table = slide.shapes.add_table(rows, cols, Inches(1), Inches(1.5), Inches(14), Inches(0.5) * rows).table
    for col_idx, col_name in enumerate(findings_table_df.columns):
        table.cell(0, col_idx).text = col_name
    for row_idx, row_data in findings_table_df.iterrows():
        for col_idx, cell_data in enumerate(row_data):
            table.cell(row_idx + 1, col_idx).text = str(cell_data)
    ppt_stream = io.BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)
    return ppt_stream

# ======================================================================================
# SECTION 5: MAIN APPLICATION LAYOUT & LOGIC
# ======================================================================================
st.title("🧬 MCC CTO Predictive QA Command Center")
st.markdown("##### An advanced analytics dashboard for strategic quality oversight, forecasting, and reporting.")

# --- LOAD DATA & MODELS ---
portfolio_df, findings_df, team_df, initiatives_df = generate_master_data()
risk_model, encoder, model_features, importance_df = get_trial_risk_model(portfolio_df)

# --- EXECUTIVE KPI METRICS ---
st.markdown("### Executive QA Program Health & Predictive Indicators")
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
risk_weights = {'Critical': 10, 'Major': 5, 'Minor': 1}
open_findings = findings_df[~findings_df['CAPA_Status'].isin(['Closed-Effective'])].copy()
open_findings['Risk_Score'] = open_findings['Risk_Level'].map(risk_weights)
total_risk_score = open_findings['Risk_Score'].sum()
kpi_col1.metric("Portfolio-wide Risk Score", f"{total_risk_score}", f"{open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0]} Open Criticals", "inverse")
overdue_major_capas = findings_df[(findings_df['CAPA_Status'] == 'Overdue') & (findings_df['Risk_Level'] != 'Minor')].shape[0]
readiness_score = max(0, 100 - (overdue_major_capas * 10) - (open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0] * 5))
kpi_col2.metric("Inspection Readiness Index", f"{readiness_score}%", f"{overdue_major_capas} Overdue Major CAPAs", "inverse")
consent_findings = findings_df[findings_df['Category'] == 'Informed Consent Process'].copy()
consent_findings['Month'] = consent_findings['Finding_Date'].dt.to_period('M')
current_month_findings = consent_findings[consent_findings['Month'] == consent_findings['Month'].max()].shape[0] if not consent_findings.empty else 0
previous_month_findings = consent_findings[consent_findings['Month'] == (consent_findings['Month'].max() - 1)].shape[0] if len(consent_findings['Month'].unique()) > 1 else 0
delta = current_month_findings - previous_month_findings
kpi_col3.metric("Consent Process Drift", f"{current_month_findings} this month", f"{delta:+} vs last month", "inverse")
team_df['Strain'] = (team_df['Audits_Conducted_YTD'] * team_df['Avg_Report_Turnaround_Days']) / 100
avg_strain = team_df['Strain'].mean()
kpi_col4.metric("Avg. Resource Strain Index", f"{avg_strain:.2f}", f"Target < 4.0", "normal")
st.markdown("---")

# --- TABS FOR DETAILED ANALYSIS, MAPPED TO ROLE RESPONSIBILITIES ---
tab1, tab2, tab3 = st.tabs(["**🔮 FORECASTING & PREDICTIVE ANALYTICS**", "**📊 AUDIT INTELLIGENCE & SYSTEMIC TRENDS**", "**👥 ORGANIZATIONAL CAPABILITY & STRATEGY**"])

with tab1:
    st.header("Forecasting & Predictive Analytics")
    st.markdown("_Leveraging data science to anticipate future risks and resource needs, enabling proactive quality management._")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Time-Series Forecast of Audit Findings")
        st.info("**Actionable Insight:** This Prophet forecast predicts the volume of audit findings for the next 12 months. This is crucial for annual budget planning, justifying resource requests, and managing leadership expectations.")
        with st.spinner("Generating 12-month forecast..."):
            forecast_fig = generate_prophet_forecast_plot(findings_df)
            st.plotly_chart(forecast_fig, use_container_width=True)
    with col2:
        st.subheader("Predict Inherent Risk of a New Trial")
        st.info("**Actionable Insight:** Use this model at study startup to forecast the likelihood of a trial generating major/critical findings, allowing for proactive allocation of QA resources.")
        p_type = st.selectbox("Trial Type", portfolio_df['Trial_Type'].unique(), key='p_type')
        p_phase = st.selectbox("Trial Phase", portfolio_df['Phase'].unique(), key='p_phase')
        p_pi_exp = st.selectbox("PI Experience", portfolio_df['PI_Experience_Level'].unique(), key='p_pi')
        if st.button("🔬 Forecast Risk Profile", type="primary"):
            input_data = {'Trial_Type': [p_type], 'Phase': [p_phase], 'PI_Experience_Level': [p_pi_exp], 'Is_First_In_Human': [False], 'Num_Sites': [1]}
            input_df = pd.DataFrame(input_data)
            input_encoded = pd.DataFrame(encoder.transform(input_df[['Trial_Type', 'Phase', 'PI_Experience_Level']]), columns=encoder.get_feature_names_out(['Trial_Type', 'Phase', 'PI_Experience_Level']))
            input_final = pd.concat([input_df.drop(columns=['Trial_Type', 'Phase', 'PI_Experience_Level']).reset_index(drop=True), input_encoded], axis=1)
            input_aligned = input_final.reindex(columns=model_features, fill_value=0)
            prediction_proba = risk_model.predict_proba(input_aligned)[0][1]
            st.plotly_chart(plot_risk_gauge(prediction_proba, "Predicted Risk of Major Findings"), use_container_width=True)

with tab2:
    st.header("Audit Intelligence & Systemic Trend Analysis")
    st.markdown("_Overseeing the internal QA Team... Partners closely with... Disease Team Leaders... to develop and implement quality frameworks._")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Systemic Process Control (SPC)")
        st.info("**Actionable Insight:** SPC charts reveal if a process is stable or degrading. Points above the red 'Upper Control Limit' (UCL) are not random; they signal a 'special cause' that must be investigated.")
        category_to_monitor = st.selectbox("Select Finding Category to Analyze for Trends:", options=findings_df['Category'].unique())
        st.plotly_chart(plot_spc_chart(findings_df, 'Finding_Date', 'Category', category_to_monitor, f"SPC p-Chart for '{category_to_monitor}' Findings"), use_container_width=True)
    with col2:
        st.subheader("Cross-Portfolio Finding Analysis")
        st.info("**Actionable Insight:** This heatmap pinpoints which Disease Teams struggle with specific compliance areas, suggesting a need for targeted training.")
        st.plotly_chart(plot_findings_heatmap_by_team(findings_df), use_container_width=True)

with tab3:
    st.header("Organizational Capability & Strategic Initiatives")
    st.markdown("_Manages operations... supervising, maintaining and developing clinical staff... Leads transformational efforts in QA..._")
    st.subheader("Auditor Workload & Performance Quadrant")
    st.info("**Actionable Insight:** This chart visualizes the Resource Strain Index. Auditors in the top-right quadrant ('High Strain') are potential burnout risks. This is a data-driven tool to justify hiring, reassign work, or provide support before a problem occurs.")
    fig = px.scatter(team_df, x='Audits_Conducted_YTD', y='Avg_Report_Turnaround_Days', size='Strain', color='Strain', text='Auditor', title='<b>QA Team Resource & Strain Analysis</b>',
                     labels={'Audits_Conducted_YTD': 'Audits Conducted (Workload)', 'Avg_Report_Turnaround_Days': 'Avg. Report Turnaround (Efficiency)'}, color_continuous_scale=px.colors.sequential.OrRd)
    fig.update_traces(textposition='top center'); fig.add_hline(y=team_df['Avg_Report_Turnaround_Days'].mean(), line_dash="dot"); fig.add_vline(x=team_df['Audits_Conducted_YTD'].mean(), line_dash="dot")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Strategic Initiatives & Budgetary Control")
    st.info("**Actionable Insight:** This provides a clear view of strategic project health. The 'Forecasted Spend' indicates if a project is on track to go over budget, allowing for proactive intervention.")
    initiatives_df['Forecasted_Spend'] = initiatives_df.apply(lambda row: (row['Spent_USD'] / row['Percent_Complete'] * 100) if row['Percent_Complete'] > 0 else 0, axis=1)
    st.dataframe(initiatives_df[['Initiative', 'Lead', 'Status', 'Budget_USD', 'Spent_USD', 'Forecasted_Spend']], use_container_width=True)

# ============================ SIDEBAR & REPORTING ============================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/e/e0/UC_San_Diego_Health_logo.svg/1200px-UC_San_Diego_Health_logo.svg.png", use_container_width=True)
st.sidebar.markdown("### About this Dashboard")
st.sidebar.info("This **Predictive QA Command Center** leverages advanced analytics to empower the Assistant Director of QA. It is designed to facilitate proactive risk management, data-driven resource allocation, and a state of continuous inspection readiness.")
st.sidebar.markdown("---")
st.sidebar.header("Generate Executive Report")
st.sidebar.info("Click the button below to download a PowerPoint summary of the current QA program status for leadership review.")
kpi_data_for_report = [("Portfolio Risk Score", total_risk_score, f"{open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0]} Open Criticals"), ("Inspection Readiness", f"{readiness_score}%", f"{overdue_major_capas} Overdue Major CAPAs"), ("Consent Process Drift", current_month_findings, f"{delta:+} vs Last Month"), ("Resource Strain Index", f"{avg_strain:.2f}", "Target < 4.0")]
findings_for_report = findings_df[(findings_df['Risk_Level'].isin(['Major', 'Critical'])) & (findings_df['CAPA_Status'] != 'Closed-Effective')][['Trial_ID', 'Category', 'Risk_Level', 'CAPA_Status']].head(10)
default_spc_fig = plot_spc_chart(findings_df, 'Finding_Date', 'Category', 'Informed Consent Process', "SPC Chart: Informed Consent Findings")
with st.sidebar, st.spinner("Generating PowerPoint report..."):
    ppt_buffer = generate_ppt_report(kpi_data_for_report, default_spc_fig, findings_for_report)
    st.download_button(label="📥 Download PowerPoint Report", data=ppt_buffer, file_name=f"MCC_CTO_QA_Summary_{datetime.date.today()}.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

st.sidebar.markdown("---")
st.sidebar.markdown("### Key Concepts & Acronyms")
st.sidebar.markdown("""
- **Prophet:** Time-series forecasting model
- **SPC:** Statistical Process Control
- **RBQM:** Risk-Based Quality Management
- **GCP:** Good Clinical Practice (ICH E6)
- **CFR:** Code of Federal Regulations
- **DSMC:** Data & Safety Monitoring Committee
- **IIT:** Investigator-Initiated Trial
- **CAPA:** Corrective and Preventive Action
""")
