Scientific QA Command Center
An advanced analytics dashboard for proactive Quality Assurance (QA) management in a Clinical Trials Office (CTO).
![alt text](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)
Table of Contents
Overview
Key Features
Technical Stack
Installation and Setup
Prerequisites
Installation Steps
Running the Application
Project Structure
Key Concepts
Overview
The Scientific QA Command Center is a Streamlit-based web application designed to provide the leadership of a Clinical Trials Office with a data-driven, interactive platform for quality oversight. It moves beyond traditional, reactive QA methods by integrating predictive analytics, statistical process control, and performance benchmarking.
The dashboard simulates a realistic CTO environment, including a portfolio of clinical trials, audit findings, QA team metrics, and strategic initiatives. This allows for a robust demonstration of modern QA principles and their impact on clinical trial performance.
Key Features
The application is organized into several modules, each providing a unique analytical perspective:
Executive Command Center (Home): A high-level dashboard with Key Performance Indicators (KPIs) like a portfolio-wide risk score, an inspection readiness index, and a resource strain index. It also features a real-time alert system for high-priority issues.
Predictive Analytics:
Utilizes a scikit-learn logistic regression model to forecast the inherent risk of new clinical trials based on their protocol characteristics (e.g., phase, PI experience).
Provides model performance metrics (F1 Score via cross-validation) for transparency.
Systemic Risk Analysis:
Statistical Process Control (SPC) Charts: Monitors the number of findings over time to distinguish between normal process variation and 'special cause' events that require investigation.
Finding Concentration Heatmap: Identifies systemic weaknesses by visualizing which types of findings are most common within specific disease teams.
CAPA Effectiveness Analysis: Calculates the recurrence rate of findings after a Corrective and Preventive Action (CAPA) has been closed, measuring the true effectiveness of remediation efforts.
Interactive eTMF Simulation: Simulates a high-pressure regulatory inspection, allowing users to test document retrieval readiness from a mock electronic Trial Master File.
PI Performance Oversight: Provides granular performance metrics for individual Principal Investigators, benchmarked against their disease team peers to facilitate targeted coaching and support.
Team & Strategy:
Auditor Workload Analysis: A quadrant analysis plot that visualizes auditor workload vs. efficiency to identify team members who are overworked, underutilized, or are candidates for mentorship.
Strategic Initiatives Dashboard: Tracks the progress and financial health of key QA projects using Earned Value Management metrics like CPI (Cost Performance Index) and SPI (Schedule Performance Index).
Quality Impact: Correlates quality metrics with operational outcomes to demonstrate the tangible link between high-quality conduct and trial success.
PowerPoint Report Generation: Allows users to download a pre-formatted executive summary of the current QA status as a .pptx file for leadership briefings.

Key Concepts
This dashboard is built around several key concepts from modern Quality Management Systems (QMS) and project management:
RBQM (Risk-Based Quality Management): An approach that focuses QA resources on the most critical risks to patient safety and data integrity.
SPC (Statistical Process Control): A method for monitoring, controlling, and improving a process through statistical analysis.
CAPA (Corrective and Preventive Action): A systematic process for investigating and correcting discrepancies (findings) to prevent their recurrence.
CPI/SPI (Cost/Schedule Performance Index): Metrics from Earned Value Management used to assess the financial and timeline health of a project. A value > 1.0 is favorable.
GCP (Good Clinical Practice): An international ethical and scientific quality standard for designing, conducting, recording, and reporting trials that involve human subjects.
