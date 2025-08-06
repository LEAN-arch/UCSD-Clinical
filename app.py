import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime
import io
import time
import logging
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import cross_val_score
from streamlit_option_menu import option_menu

# Ensure Plotly and Kaleido are available
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError as e:
    st.error("Plotly or Kaleido is not installed. Please install with `pip install plotly kaleido`.")
    raise e

# ======================================================================================
# SECTION 1: APP CONFIGURATION & STYLING
# ======================================================================================
st.set_page_config(
    page_title="MCC CTO QA Command Center",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main .block-container { padding: 1rem 2rem 2rem; max-width: 1400px; }
    .stMetric { background-color: #FAFAFA; border: 1px solid #E0E0E0; border-left: 5px solid #005A9C; border-radius: 8px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# ======================================================================================
# SECTION 1.5: SUPPRESS VERBOSE LOGGING
# ======================================================================================
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

# ======================================================================================
# SECTION 2: DATA SIMULATION
# ======================================================================================
@st.cache_data(ttl=3600, persist=True)  # Increased TTL to 1 hour and persist for static data
def generate_master_data():
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
    pis_by_team = {team: [f'Dr. {team_initials}{i}' for i in range(1, 5)] for team, team_initials in zip(portfolio_df['Disease_Team'].unique(), ['L', 'U', 'B', 'GI', 'GU', 'M'])}
    portfolio_df['PI_Name'] = portfolio_df.apply(lambda row: np.random.choice(pis_by_team[row['Disease_Team']]), axis=1)
    
    # Ensure every trial has at least 4 findings for consistency
    findings_trial_ids = trial_ids * 4 + np.random.choice(trial_ids, 250 - len(trial_ids) * 4).tolist()
    np.random.shuffle(findings_trial_ids)
    finding_categories = ['Informed Consent Process', 'Source Data Verification', 'Investigational Product Accountability', 'Regulatory Binder Mgmt', 'AE/SAE Reporting', 'Protocol Adherence']
    max_days = (datetime.date(2025, 8, 6) - datetime.date(2022, 1, 1)).days  # Cap dates before 2025-08-06
    findings_data = {
        'Finding_ID': [f'FIND-{i:04d}' for i in range(1, 251)],
        'Trial_ID': findings_trial_ids[:250],
        'Category': np.random.choice(finding_categories, 250, p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1]),
        'Risk_Level': np.random.choice(['Critical', 'Major', 'Minor'], 250, p=[0.05, 0.35, 0.6]),
        'CAPA_Status': np.random.choice(['Open', 'Pending Verification', 'Closed-Effective', 'Overdue'], 250, p=[0.15, 0.1, 0.7, 0.05]),
        'Finding_Date': pd.to_datetime([datetime.date(2022, 1, 1) + datetime.timedelta(days=int(d)) for d in np.random.randint(0, max_days, 250)])
    }
    findings_df = pd.DataFrame(findings_data).merge(portfolio_df[['Trial_ID', 'Disease_Team', 'Trial_Type', 'PI_Name']], on='Trial_ID', how='left')
    major_finding_trials = findings_df[findings_df['Risk_Level'].isin(['Major', 'Critical'])]['Trial_ID'].unique()
    portfolio_df['Had_Major_Finding'] = portfolio_df['Trial_ID'].isin(major_finding_trials).astype(int)
    auditors = ['Jane Doe, RN', 'John Smith, PhD', 'Maria Garcia, MPH', 'Kevin Lee, CCRC']
    team_data = {
        'Auditor': auditors,
        'Audits_Conducted_YTD': np.random.randint(15, 30, len(auditors)),
        'Avg_Report_Turnaround_Days': np.random.uniform(8, 20, len(auditors)),
        'GCP_Certification_Status': np.random.choice(['Current', 'Expires <90d'], len(auditors), p=[0.75, 0.25]),
        'IIT_Oversight_Skill': np.random.randint(3, 6, len(auditors)),
        'FDA_Inspection_Mgmt_Skill': np.random.randint(2, 5, len(auditors))
    }
    team_df = pd.DataFrame(team_data)
    initiatives_data = {
        'Initiative': ['eQMS Implementation', 'Auditor Training Program Revamp', 'Inspection Readiness Mock Audits', 'IIT Risk-Based Monitoring Plan'],
        'Lead': ['Jane Doe, RN', 'John Smith, PhD', 'Maria Garcia, MPH', 'Kevin Lee, CCRC'],
        'Status': ['On Track', 'At Risk', 'Completed', 'On Track'],
        'Percent_Complete': [60, 85, 100, 30],
        'Start_Date': pd.to_datetime(['2023-01-15', '2023-03-01', '2023-06-01', '2023-09-01']),
        'End_Date': pd.to_datetime(['2024-06-30', '2023-11-30', '2023-08-31', '2024-03-31']),
        'Budget_USD': [75000, 15000, 25000, 10000],
        'Spent_USD': [40000, 14000, 23500, 2500]
    }
    initiatives_df = pd.DataFrame(initiatives_data)
    return portfolio_df, findings_df, team_df, initiatives_df

# ======================================================================================
# SECTION 3: ANALYTICAL & PLOTTING FUNCTIONS
# ======================================================================================
@st.cache_resource
def get_trial_risk_model(_portfolio_df):
    features = ['Trial_Type', 'Phase', 'PI_Experience_Level', 'Is_First_In_Human', 'Num_Sites', 'Subjects_Enrolled']  # Added Subjects_Enrolled
    target = 'Had_Major_Finding'
    X, y = _portfolio_df[features], _portfolio_df[target]
    categorical_features = ['Trial_Type', 'Phase', 'PI_Experience_Level']
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    X_encoded = pd.DataFrame(encoder.fit_transform(X[categorical_features]), columns=encoder.get_feature_names_out(categorical_features))
    X_final = pd.concat([X.drop(columns=categorical_features).reset_index(drop=True), X_encoded], axis=1)
    model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    model.fit(X_final, y)
    # Add model evaluation
    scores = cross_val_score(model, X_final, y, cv=5, scoring='f1')
    st.write(f"Model F1 Score (5-fold CV): {scores.mean():.2f} ± {scores.std():.2f}")
    return model, encoder, X_final.columns

def plot_spc_chart_sme(df, date_col, category_col, value, title):
    df_filtered = df[df[category_col] == value].copy()
    df_filtered = df_filtered.set_index(date_col).sort_index()
    # Zero-fill missing months
    date_range = pd.date_range(start=df_filtered.index.min(), end=df_filtered.index.max(), freq='ME')
    monthly_counts = df_filtered.resample('ME').size().reindex(date_range, fill_value=0).reset_index(name='findings')
    # Use 'index' as the date column name after reindex
    monthly_counts['month'] = monthly_counts['index'].dt.to_period('M').astype(str)
    if monthly_counts.empty or monthly_counts['findings'].sum() == 0:
        return go.Figure().update_layout(title=f'<b>{title}</b><br>No data available.')
    p_bar, std_dev = monthly_counts['findings'].mean(), np.sqrt(monthly_counts['findings'].mean())
    UCL, LCL = p_bar + 3 * std_dev, max(0, p_bar - 3 * std_dev)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_counts['month'], y=[UCL]*len(monthly_counts), mode='lines', line=dict(color='rgba(255, 100, 100, 0.5)'), showlegend=False, hoverinfo='none'))
    fig.add_trace(go.Scatter(x=monthly_counts['month'], y=[LCL]*len(monthly_counts), mode='lines', line=dict(color='rgba(255, 100, 100, 0.5)'), fill='tonexty', fillcolor='rgba(0, 176, 246, 0.1)', name='Common Cause Variation Zone', hoverinfo='none'))
    fig.add_trace(go.Scatter(x=monthly_counts['month'], y=[p_bar]*len(monthly_counts), mode='lines', name='Process Mean', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=monthly_counts['month'], y=[UCL]*len(monthly_counts), mode='lines', name='Upper Control Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=monthly_counts['month'], y=[LCL]*len(monthly_counts), mode='lines', name='Lower Control Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=monthly_counts['month'], y=monthly_counts['findings'], mode='lines+markers', name='Monthly Findings', line=dict(color='#005A9C'), hovertemplate="<b>%{x}</b><br>Findings: %{y}<br>Status: In Control<extra></extra>"))
    out_of_control = monthly_counts[monthly_counts['findings'] > UCL]
    if not out_of_control.empty:
        fig.add_trace(go.Scatter(x=out_of_control['month'], y=out_of_control['findings'], mode='markers', name='Out of Control Signal', marker=dict(color='red', size=12, symbol='x', line=dict(width=3)), hovertemplate="<b>%{x}</b><br>Findings: %{y}<br>Status: <b>Out of Control</b><extra></extra>"))
    fig.update_layout(title=f'<b>{title}</b>', xaxis_title=None, yaxis_title='Number of Findings', plot_bgcolor='white', height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def generate_ppt_report(kpi_data, spc_fig, findings_table_df):
    try:
        prs = Presentation()
        prs.slide_width = Inches(16)
        prs.slide_height = Inches(9)
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        slide.shapes.title.text = "MCC CTO Quality Assurance Executive Summary"
        slide.placeholders[1].text = f"Report Generated: {datetime.date.today().strftime('%Y-%m-%d')}"
        kpi_slide_layout = prs.slide_layouts[5]
        slide = prs.slides.add_slide(kpi_slide_layout)
        slide.shapes.title.text = "QA Program Health Dashboard"
        positions = [(Inches(1), Inches(1.5)), (Inches(5), Inches(1.5)), (Inches(9), Inches(1.5)), (Inches(13), Inches(1.5))]
        for i, (kpi_title, kpi_val, kpi_delta) in enumerate(kpi_data):
            txBox = slide.shapes.add_textbox(positions[i][0], positions[i][1], Inches(3.5), Inches(2))
            tf = txBox.text_frame
            tf.word_wrap = True
            p1 = tf.paragraphs[0]
            p1.text = kpi_title
            p1.font.bold = True
            p1.font.size = Pt(20)
            p2 = tf.add_paragraph()
            p2.text = str(kpi_val)
            p2.font.size = Pt(44)
            p2.font.bold = True
            p3 = tf.add_paragraph()
            p3.text = str(kpi_delta)
            p3.font.size = Pt(16)
        chart_slide_layout = prs.slide_layouts[5]
        slide = prs.slides.add_slide(chart_slide_layout)
        slide.shapes.title.text = "Systemic Process Control (SPC) Analysis"
        try:
            image_stream = io.BytesIO()
            spc_fig.write_image(image_stream, format='png', scale=1)  # Reduced scale for consistency
            image_stream.seek(0)
            slide.shapes.add_picture(image_stream, Inches(1), Inches(1.5), width=Inches(14))
        except (RuntimeError, ValueError) as e:
            txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(14), Inches(4))
            tf = txBox.text_frame
            p = tf.add_paragraph()
            p.text = "Chart Generation Failed: Missing Dependency"
            p.font.bold = True
            p.font.size = Pt(24)
            p.font.color.rgb = RGBColor(255, 0, 0)
            p = tf.add_paragraph()
            p.text = ("The 'Kaleido' library requires Google Chrome/Chromium to export this chart. The app environment is likely missing this dependency.\n"
                      "To fix, update requirements.txt with: 'kaleido==0.2.1' and ensure Chrome is installed.")
            p.font.size = Pt(18)
        table_slide_layout = prs.slide_layouts[5]
        slide = prs.slides.add_slide(table_slide_layout)
        slide.shapes.title.text = "High-Priority Open Findings (Critical/Major)"
        rows, cols = findings_table_df.shape[0] + 1, findings_table_df.shape[1]
        table_height = min(Inches(6), Inches(0.4) * rows)  # Dynamic table height
        table = slide.shapes.add_table(rows, cols, Inches(1), Inches(1.5), Inches(14), table_height).table
        for col_idx, col_name in enumerate(findings_table_df.columns):
            table.cell(0, col_idx).text = col_name
        for ppt_row_idx, df_row in enumerate(findings_table_df.itertuples(index=False), start=1):
            for col_idx, cell_data in enumerate(df_row):
                table.cell(ppt_row_idx, col_idx).text = str(cell_data)
        ppt_stream = io.BytesIO()
        prs.save(ppt_stream)
        ppt_stream.seek(0)
        return ppt_stream
    except Exception as e:
        st.error(f"Failed to generate PowerPoint report: {str(e)}")
        return None

def plot_pi_findings_barchart_sme(pi_findings, pi_name):
    if pi_findings.empty:
        return go.Figure().update_layout(title=f'No findings recorded for {pi_name}', annotations=[dict(text="No Data", x=0.5, y=0.5, showarrow=False, font_size=20)])
    category_counts = pi_findings['Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']
    fig = px.bar(category_counts.sort_values('Count'), x='Count', y='Category', orientation='h', title=f'<b>Finding Breakdown for {pi_name}</b>', text='Count', labels={'Count': 'Number of Findings', 'Category': 'Finding Category'})
    fig.update_traces(marker_color='#005A9C', textposition='outside')
    fig.update_layout(plot_bgcolor='white', yaxis={'categoryorder': 'total ascending'})
    return fig

def plot_auditor_strain_sme(team_df):
    # Refined strain calculation
    team_df['Strain'] = (team_df['Audits_Conducted_YTD'] * team_df['Avg_Report_Turnaround_Days'] / (team_df['IIT_Oversight_Skill'] + team_df['FDA_Inspection_Mgmt_Skill'])).round(2)
    fig = px.scatter(team_df, x='Audits_Conducted_YTD', y='Avg_Report_Turnaround_Days', size='Strain', color='Strain', text='Auditor', title='<b>Auditor Performance & Workload Quadrant Analysis</b>', labels={'Audits_Conducted_YTD': 'Audits Conducted (Workload)', 'Avg_Report_Turnaround_Days': 'Avg. Report Turnaround Time (Efficiency)'}, color_continuous_scale=px.colors.sequential.OrRd, hovertemplate="<b>%{text}</b><br>Audits: %{x}<br>Avg. Turnaround: %{y:.1f} days<br>Strain Index: %{marker.size:.1f}<extra></extra>")
    mean_x, mean_y = team_df['Audits_Conducted_YTD'].mean(), team_df['Avg_Report_Turnaround_Days'].mean()
    fig.add_hline(y=mean_y, line_dash="dot", line_color="grey", annotation_text="Avg. Efficiency")
    fig.add_vline(x=mean_x, line_dash="dot", line_color="grey", annotation_text="Avg. Workload")
    fig.add_annotation(x=mean_x*1.2, y=mean_y*1.2, text="<b>High Strain</b><br>(At Risk of Burnout)", showarrow=False, font=dict(color="firebrick"))
    fig.add_annotation(x=mean_x*1.2, y=mean_y*0.8, text="<b>Top Performers</b><br>(Potential Mentors)", showarrow=False, font=dict(color="darkgreen"))
    fig.add_annotation(x=mean_x*0.8, y=mean_y*0.8, text="<b>Underutilized</b><br>(Capacity for Growth)", showarrow=False, font=dict(color="darkblue"))
    fig.add_annotation(x=mean_x*0.8, y=mean_y*1.2, text="<b>Needs Coaching</b><br>(Efficiency Opportunity)", showarrow=False, font=dict(color="goldenrod"))
    fig.update_traces(textposition='top center')
    fig.update_layout(plot_bgcolor='white', height=500)
    return fig

# ======================================================================================
# SECTION 4: UI PAGE RENDERING FUNCTIONS
# ======================================================================================
def render_command_center(portfolio_df, findings_df, team_df):
    st.subheader("Executive Command Center", divider="blue")
    st.markdown("A strategic overview of the QA program's current status and highest priority items.")
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    risk_weights = {'Critical': 10, 'Major': 5, 'Minor': 1}
    open_findings = findings_df[~findings_df['CAPA_Status'].isin(['Closed-Effective'])].copy()
    open_findings['Risk_Score'] = open_findings['Risk_Level'].map(risk_weights)
    total_risk_score = int(open_findings['Risk_Score'].sum())
    overdue_major_capas = findings_df[(findings_df['CAPA_Status'] == 'Overdue') & (findings_df['Risk_Level'] != 'Minor')].shape[0]
    readiness_score = max(0, 100 - (overdue_major_capas * 10) - (open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0] * 5))
    team_df['Strain'] = (team_df['Audits_Conducted_YTD'] * team_df['Avg_Report_Turnaround_Days'] / (team_df['IIT_Oversight_Skill'] + team_df['FDA_Inspection_Mgmt_Skill'])).round(2)
    avg_strain = team_df['Strain'].mean()
    kpi_col1.metric("Portfolio-wide Risk Score", f"{total_risk_score}", f"{open_findings[open_findings['Risk_Level'] == 'Critical'].shape[0]} Open Criticals", delta_color="inverse")
    kpi_col2.metric("Inspection Readiness Index", f"{readiness_score}%", f"{overdue_major_capas} Overdue Major CAPAs", delta_color="inverse")
    kpi_col3.metric("Avg. Resource Strain Index", f"{avg_strain:.2f}", "Target < 4.0", delta_color="normal")
    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### 🚨 High-Priority Alerts")
        overdue_findings = findings_df[(findings_df['CAPA_Status'] == 'Overdue') & (findings_df['Risk_Level'] != 'Minor')].sort_values(by='Finding_Date').reset_index()
        if not overdue_findings.empty:
            finding = overdue_findings.iloc[0]
            st.error(f"**Overdue CAPA:** Finding `{finding['Finding_ID']}` on trial `{finding['Trial_ID']}` ({finding['Risk_Level']}) is overdue.", icon="🔥")
        most_strained = team_df.sort_values(by='Strain', ascending=False).iloc[0]
        if most_strained['Strain'] > 5.0:
            st.warning(f"**Resource At Risk:** `{most_strained['Auditor']}` has a high Strain Index of `{most_strained['Strain']:.2f}`.", icon="⚠️")
        criticals_per_trial = findings_df[findings_df['Risk_Level'] == 'Critical'].groupby('Trial_ID').size().sort_values(ascending=False)
        if not criticals_per_trial.empty:
            trial_id, count = criticals_per_trial.index[0], criticals_per_trial.iloc[0]
            st.error(f"**High-Risk Trial:** Trial `{trial_id}` has `{count}` open critical findings.", icon="🔬")
    with col2:
        st.markdown("#### Portfolio Status")
        status_counts = portfolio_df['Status'].value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title='Active Clinical Trial Portfolio', hole=0.4, color_discrete_map={'Enrolling': '#005A9C', 'Follow-up': '#3EC1D3', 'Closed to Accrual': '#FFC72C', 'Suspended': '#E63946'})
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

def render_predictive_analytics(portfolio_df):
    st.subheader("Predictive Analytics", divider="blue")
    st.markdown("_This section utilizes predictive modeling to quantify inherent trial risk, enabling a proactive, data-driven approach to quality management._")
    risk_model, encoder, model_features = get_trial_risk_model(portfolio_df)
    with st.container(border=True):
        st.markdown("##### Inherent Risk Prediction for New Trials")
        st.info("💡 **Expert Tip:** Use this tool to triage new protocols. A predicted risk score > 60% may warrant assigning a more senior auditor or increasing the monitoring frequency from the start.", icon="❓")
        with st.form("risk_predictor_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                p_type = st.selectbox("Trial Type", portfolio_df['Trial_Type'].unique(), key='p_type').strip()
            with col2:
                p_phase = st.selectbox("Trial Phase", portfolio_df['Phase'].unique(), key='p_phase').strip()
            with col3:
                p_pi_exp = st.selectbox("PI Experience", portfolio_df['PI_Experience_Level'].unique(), key='p_pi').strip()
            if st.form_submit_button("🔬 Forecast Risk Profile"):
                if not all([p_type, p_phase, p_pi_exp]):
                    st.error("Please fill all fields before forecasting.")
                else:
                    input_df = pd.DataFrame({
                        'Trial_Type': [p_type],
                        'Phase': [p_phase],
                        'PI_Experience_Level': [p_pi_exp],
                        'Is_First_In_Human': [False],
                        'Num_Sites': [1],
                        'Subjects_Enrolled': [50]  # Default value for new feature
                    })
                    input_encoded = pd.DataFrame(encoder.transform(input_df[['Trial_Type', 'Phase', 'PI_Experience_Level']]), columns=encoder.get_feature_names_out(['Trial_Type', 'Phase', 'PI_Experience_Level']))
                    input_final = pd.concat([input_df.drop(columns=['Trial_Type', 'Phase', 'PI_Experience_Level']).reset_index(drop=True), input_encoded], axis=1).reindex(columns=model_features, fill_value=0)
                    prediction_proba = risk_model.predict_proba(input_final)[0][1]
                    st.success(f"Predicted Risk of a Major Finding: **{prediction_proba:.1%}**")

def render_systemic_risk(findings_df, portfolio_df):
    st.subheader("Systemic Process & Risk Analysis", divider="blue")
    st.markdown("_This section moves beyond individual data points to identify systemic trends, process vulnerabilities, and non-random patterns across the clinical trial portfolio._")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### Statistical Process Control (SPC) Analysis")
            st.info("💡 **Expert Tip:** Any red 'X' points outside the shaded blue area represent 'special cause' variations that require immediate Root Cause Analysis.", icon="❓")
            category_to_monitor = st.selectbox("Select Finding Category to Analyze for Trends:", options=findings_df['Category'].unique())
            st.plotly_chart(plot_spc_chart_sme(findings_df, 'Finding_Date', 'Category', category_to_monitor, f"SPC for '{category_to_monitor}'"), use_container_width=True)
    with col2:
        with st.container(border=True):
            st.markdown("##### Finding Concentration Analysis")
            st.info("💡 **Expert Tip:** Dark blue 'hotspots' suggest a targeted training intervention for that specific team is more effective than a CTO-wide initiative.", icon="❓")
            st.plotly_chart(px.imshow(pd.crosstab(findings_df['Disease_Team'], findings_df['Category']), text_auto=True, aspect="auto", title="<b>Finding Concentration by Disease Team & Category</b>", color_continuous_scale='Blues'), use_container_width=True)
    with st.container(border=True):
        st.markdown("##### Interactive Regulatory Inspection Simulation")
        st.info("💡 **Expert Tip:** Use this tool to pressure-test readiness and train staff. Can the requested document be produced instantly? This simulates the high-stakes reality of an FDA or EMA audit.", icon="❓")
        @st.cache_data
        def create_mock_etmf(_portfolio_df):
            mock_etmf = {}
            for _, row in _portfolio_df.iterrows():
                trial_id, num_subjects = row['Trial_ID'], row['Subjects_Enrolled']
                mock_etmf[trial_id] = {
                    "Protocol Signature Page": f"DocRef_PSP_{trial_id}.pdf",
                    "IRB Approval Letter": f"DocRef_IRB_Approval_{trial_id}.pdf",
                    "FDA Form 1572": f"DocRef_1572_{trial_id}.pdf" if "IIT" in trial_id or "IND" in trial_id else "N/A",
                    "Informed Consent Forms": {f"Subject-{i:03d}": f"ICF_{trial_id}_Subj_{i:03d}.pdf" for i in range(1, num_subjects + 1)},
                    "Serious Adverse Event Reports": {f"SAE-{i:03d}": f"SAE_{trial_id}_{i:03d}.pdf" for i in range(1, np.random.randint(2, 6))}
                }
            return mock_etmf
        mock_etmf_db = create_mock_etmf(portfolio_df)
        sim_col1, sim_col2 = st.columns([1, 2])
        with sim_col1:
            st.write("**Inspection Scenario:**")
            trial_to_inspect = st.selectbox("Select a Trial to Inspect:", options=portfolio_df['Trial_ID'], key="inspect_trial")
            subject_list = list(mock_etmf_db[trial_to_inspect]["Informed Consent Forms"].keys())
            subject_to_inspect = st.selectbox("Select a Subject:", options=subject_list, key="inspect_subject") if subject_list else None
        if subject_to_inspect and st.button("🔬 Pull Subject's Consent Form"):
            with sim_col2:
                st.info(f"Request: 'Please provide the signed consent form for {subject_to_inspect} on trial {trial_to_inspect}.'")
                with st.spinner("Searching eTMF..."):
                    time.sleep(1.5)
                st.success("**Document Found!**")
                st.code(f"File Path: /eTMF/Trials/{trial_to_inspect}/Subject_Files/{subject_to_inspect}/ICF_{trial_to_inspect}_Subj_{subject_to_inspect.split('-')[1]}.pdf\nAccessed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", language="bash")
        if st.button("📄 Pull Trial's 1572 Form"):
            with sim_col2:
                st.info(f"Request: 'Please provide the current FDA Form 1572 for trial {trial_to_inspect}.'")
                with st.spinner("Searching eTMF..."):
                    time.sleep(1)
                doc_ref = mock_etmf_db[trial_to_inspect].get("FDA Form 1572")
                if doc_ref != "N/A":
                    st.success("**Document Found!**")
                    st.code(f"File Path: /eTMF/Trials/{trial_to_inspect}/Regulatory/{doc_ref}\nAccessed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", language="bash")
                else:
                    st.error("**Document Not Applicable!** This is not an IND-holding trial.")

def render_pi_performance(portfolio_df, findings_df):
    st.subheader("Principal Investigator (PI) Performance Oversight", divider="blue")
    st.markdown("_This section enables granular analysis of quality metrics at the individual PI level, benchmarked against their Disease Team peers. It is a tool for targeted coaching and support._")
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("##### Select Investigator")
            if 'selected_team' not in st.session_state:
                st.session_state.selected_team = sorted(portfolio_df['Disease_Team'].unique())[0]
            selected_team = st.selectbox("Select a Disease Team:", options=sorted(portfolio_df['Disease_Team'].unique()), key="team_select", index=sorted(portfolio_df['Disease_Team'].unique()).index(st.session_state.selected_team))
            st.session_state.selected_team = selected_team
            available_pis = sorted(portfolio_df[portfolio_df['Disease_Team'] == selected_team]['PI_Name'].unique())
            selected_pi = st.selectbox("Select a PI:", options=available_pis, key="pi_select")
        pi_findings = findings_df[findings_df['PI_Name'] == selected_pi]
        team_findings = findings_df[findings_df['Disease_Team'] == selected_team]
        with col2:
            st.markdown(f"##### Performance Snapshot: {selected_pi}")
            m_col1, m_col2, m_col3 = st.columns(3)
            pi_major_findings = pi_findings[pi_findings['Risk_Level'].isin(['Major', 'Critical'])].shape[0]
            team_avg_major_findings = team_findings[team_findings['Risk_Level'].isin(['Major', 'Critical'])].groupby('PI_Name').size().mean()
            m_col1.metric("Major/Critical Findings", f"{pi_major_findings}", f"Team Avg: {team_avg_major_findings:.1f}", delta_color="inverse")
            pi_avg_closure = pi_findings['Days_to_Close'].mean() if not pi_findings.empty else 0
            team_avg_closure = team_findings['Days_to_Close'].mean() if not team_findings.empty else 0
            m_col2.metric("Avg. CAPA Closure (Days)", f"{pi_avg_closure:.1f}" if pi_avg_closure != 0 else "N/A", f"Team Avg: {team_avg_closure:.1f}", delta_color="inverse")
            pi_overdue = pi_findings[pi_findings['CAPA_Status'] == 'Overdue'].shape[0]
            team_avg_overdue = team_findings.groupby('PI_Name')['CAPA_Status'].apply(lambda x: (x == 'Overdue').sum()).mean()
            m_col3.metric("Overdue CAPAs", f"{pi_overdue}", f"Team Avg: {team_avg_overdue:.1f}", delta_color="inverse")
        st.markdown("---")
        st.info(f"💡 **Expert Tip:** How does {selected_pi}'s performance compare to their team average? Significant deviations present a data-driven opportunity for a supportive coaching conversation.", icon="❓")
        st.plotly_chart(plot_pi_findings_barchart_sme(pi_findings, selected_pi), use_container_width=True)

def render_organizational_capability(team_df, initiatives_df):
    st.subheader("Organizational Capability & Strategic Oversight", divider="blue")
    st.markdown("_This section assesses the capacity of the QA team and tracks progress and financial health of key strategic objectives._")
    with st.container(border=True):
        st.markdown("##### Auditor Workload & Performance Analysis")
        st.info("💡 **Expert Tip:** Use the quadrants to guide management. 'High Strain' auditors may need workload redistribution. 'Top Performers' are candidates for mentoring others. 'Needs Coaching' auditors could benefit from targeted training to improve efficiency.", icon="❓")
        st.plotly_chart(plot_auditor_strain_sme(team_df), use_container_width=True)
    with st.container(border=True):
        st.markdown("##### Strategic Initiatives & Financial Oversight")
        st.info("💡 **Expert Tip:** A CPI or SPI value < 1.0 indicates a project is over budget or behind schedule, respectively. This allows for proactive intervention before projects go significantly off-track.", icon="❓")
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
        st.caption("CPI (Cost Performance Index) & SPI (Schedule Performance Index): > 1.0 is favorable (green), < 1.0 is unfavorable (red).")

# ======================================================================================
# SECTION 5: MAIN APP ORCHESTRATION
# ======================================================================================
def main():
    portfolio_df, findings_df, team_df, initiatives_df = generate_master_data()
    findings_df['Closure_Date'] = findings_df.apply(lambda row: row['Finding_Date'] + pd.to_timedelta(np.random.randint(5, 60), unit='d') if row['CAPA_Status'] == 'Closed-Effective' else pd.NaT, axis=1)
    findings_df['Days_to_Close'] = (findings_df['Closure_Date'] - findings_df['Finding_Date']).dt.days.fillna(0)  # Handle NaT gracefully

    with st.sidebar:
        st.markdown("## Moores Cancer Center")
        st.markdown("### Clinical Trials Office")
        st.markdown("---")
        selected = option_menu(
            menu_title="QA Command Center",
            options=["Home", "Predictive Analytics", "Systemic Risk", "PI Performance", "Team & Strategy"],
            icons=["house-door-fill", "graph-up-arrow", "shield-shaded", "person-badge", "people-fill"],
            menu_icon="kanban-fill", default_index=0
        )
        st.markdown("---")
        st.info("This dashboard is a prototype demonstrating a proactive, data-driven approach to Clinical QA management.")
        st.header("Generate Executive Report")
        st.info("Download a PowerPoint summary of the current QA program status for leadership review.")
        
        risk_weights = {'Critical': 10, 'Major': 5, 'Minor': 1}
        open_findings_sidebar = findings_df[~findings_df['CAPA_Status'].isin(['Closed-Effective'])].copy()
        open_findings_sidebar['Risk_Score'] = open_findings_sidebar['Risk_Level'].map(risk_weights)
        total_risk_score_sidebar = int(open_findings_sidebar['Risk_Score'].sum())
        overdue_major_capas_sidebar = findings_df[(findings_df['CAPA_Status'] == 'Overdue') & (findings_df['Risk_Level'] != 'Minor')].shape[0]
        readiness_score_sidebar = max(0, 100 - (overdue_major_capas_sidebar * 10) - (open_findings_sidebar[open_findings_sidebar['Risk_Level'] == 'Critical'].shape[0] * 5))
        team_df['Strain'] = (team_df['Audits_Conducted_YTD'] * team_df['Avg_Report_Turnaround_Days'] / (team_df['IIT_Oversight_Skill'] + team_df['FDA_Inspection_Mgmt_Skill'])).round(2)
        avg_strain_sidebar = team_df['Strain'].mean()
        kpi_data_for_report = [
            ("Portfolio Risk Score", total_risk_score_sidebar, f"{open_findings_sidebar[open_findings_sidebar['Risk_Level'] == 'Critical'].shape[0]} Open Criticals"),
            ("Inspection Readiness", f"{readiness_score_sidebar}%", f"{overdue_major_capas_sidebar} Overdue Major CAPAs"),
            ("Resource Strain Index", f"{avg_strain_sidebar:.2f}", "Target < 4.0")
        ]
        findings_for_report = findings_df[(findings_df['Risk_Level'].isin(['Major', 'Critical'])) & (findings_df['CAPA_Status'] != 'Closed-Effective')][['Trial_ID', 'Category', 'Risk_Level', 'CAPA_Status']].head(10)
        default_spc_fig = plot_spc_chart_sme(findings_df, 'Finding_Date', 'Category', 'Informed Consent Process', "SPC Chart: Informed Consent Findings")
        
        ppt_buffer = generate_ppt_report(kpi_data_for_report, default_spc_fig, findings_for_report)
        if ppt_buffer:
            st.download_button(
                label="📥 Download PowerPoint Report",
                data=ppt_buffer,
                file_name=f"MCC_CTO_QA_Summary_{datetime.date.today()}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

        st.markdown("---")
        st.markdown("### Key Concepts & Regulations")
        st.markdown("- **RBQM:** Risk-Based Quality Management\n- **SPC:** Statistical Process Control\n- **CPI/SPI:** Cost/Schedule Performance Index\n- **GCP:** Good Clinical Practice\n- **2CFR Part 50 & 312:** Key FDA Regulations")

    st.title("🔬 Scientific QA Command Center")
    st.markdown("An advanced analytics dashboard for the Assistant Director of Quality Assurance.")

    if selected == "Home":
        render_command_center(portfolio_df, findings_df, team_df)
    elif selected == "Predictive Analytics":
        render_predictive_analytics(portfolio_df)
    elif selected == "Systemic Risk":
        render_systemic_risk(findings_df, portfolio_df)
    elif selected == "PI Performance":
        render_pi_performance(portfolio_df, findings_df)
    elif selected == "Team & Strategy":
        render_organizational_capability(team_df, initiatives_df)

if __name__ == "__main__":
    main()
