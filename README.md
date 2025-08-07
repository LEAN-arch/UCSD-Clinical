<div align="center">
  <h1>Scientific QA Command Center</h1>
  <p>
    <strong>An advanced analytics dashboard for proactive Quality Assurance (QA) management in a Clinical Trials Office (CTO).</strong>
  </p>
  <a href="https://ucsd-clinical.streamlit.app/">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Streamlit App">
  </a>
</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [✨ Key Features](#-key-features)
- [🛠️ Technical Stack](#️-technical-stack)
- [🚀 Installation and Setup](#-installation-and-setup)
- [🧠 Key Concepts](#-key-concepts)

---

## 📖 Overview

The **Scientific QA Command Center** is a Streamlit-based web application designed to provide the leadership of a Clinical Trials Office with a data-driven, interactive platform for quality oversight. It moves beyond traditional, reactive QA methods by integrating predictive analytics, statistical process control, and performance benchmarking.

The dashboard simulates a realistic CTO environment, including a portfolio of clinical trials, audit findings, QA team metrics, and strategic initiatives. This allows for a robust demonstration of modern QA principles and their impact on clinical trial performance.

---

## ✨ Key Features

<table>
  <tr>
    <td width="200px"><strong>📊 Executive Command Center</strong></td>
    <td>A high-level dashboard with Key Performance Indicators (KPIs) like a portfolio-wide risk score, an inspection readiness index, and a resource strain index. It also features a real-time alert system for high-priority issues.</td>
  </tr>
  <tr>
    <td><strong>🔮 Predictive Analytics</strong></td>
    <td>Utilizes a <code>scikit-learn</code> logistic regression model to forecast the inherent risk of new clinical trials based on their protocol characteristics. Provides model performance metrics (F1 Score) for transparency.</td>
  </tr>
  <tr>
    <td><strong>🔬 Systemic Risk Analysis</strong></td>
    <td>
      <ul>
        <li><strong>Statistical Process Control (SPC) Charts:</strong> Monitors findings over time to distinguish normal variation from 'special cause' events requiring investigation.</li>
        <li><strong>Finding Concentration Heatmap:</strong> Identifies systemic weaknesses by visualizing which types of findings are most common within specific disease teams.</li>
        <li><strong>CAPA Effectiveness Analysis:</strong> Measures the true effectiveness of remediation efforts by calculating finding recurrence rates post-CAPA.</li>
        <li><strong>Interactive eTMF Simulation:</strong> Simulates a high-pressure regulatory inspection, testing document retrieval readiness.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td><strong>🧑‍🔬 PI Performance Oversight</strong></td>
    <td>Provides granular performance metrics for individual Principal Investigators, benchmarked against their disease team peers to facilitate targeted coaching and support.</td>
  </tr>
  <tr>
    <td><strong>📈 Team & Strategy</strong></td>
    <td>
      <ul>
        <li><strong>Auditor Workload Analysis:</strong> A quadrant plot visualizing auditor workload vs. efficiency to identify team members who are overworked or are candidates for mentorship.</li>
        <li><strong>Strategic Initiatives Dashboard:</strong> Tracks the progress and financial health of key QA projects using Earned Value Management metrics (CPI/SPI).</li>
      </ul>
    </td>
  </tr>
    <tr>
    <td><strong>🔗 Quality Impact</strong></td>
    <td>Correlates quality metrics with operational outcomes to demonstrate the tangible link between high-quality conduct and trial success.</td>
  </tr>
  <tr>
    <td><strong>📄 PowerPoint Report Generation</strong></td>
    <td>Allows users to download a pre-formatted executive summary of the current QA status as a <code>.pptx</code> file for leadership briefings.</td>
  </tr>
</table>

---

## 🛠️ Technical Stack

| Category                | Technologies                                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Framework**           | <code>Streamlit</code>                                                                                                                                                   |
| **Data Manipulation**   | <code>Pandas</code>, <code>NumPy</code>                                                                                                                                  |
| **Data Visualization**  | <code>Plotly</code>                                                                                                                                                      |
| **Machine Learning**    | <code>Scikit-learn</code>                                                                                                                                                |
| **PowerPoint Generation** | <code>python-pptx</code>                                                                                                                                                 |
| **UI Components**       | <code>streamlit-option-menu</code>                                                                                                                                       |

---

## 🚀 Installation and Setup

<blockquote>
  <p><strong>Prerequisites:</strong> Python 3.9+ and the <code>pip</code> package manager are required.</p>
</blockquote>

1.  **Clone the repository:**
    <pre><code class="lang-bash">git clone &lt;your-repository-url&gt;
cd &lt;repository-directory&gt;</code></pre>

2.  **Create and activate a virtual environment (Recommended):**
    <pre><code class="lang-bash"># For Unix/macOS
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate</code></pre>

3.  **Install Dependencies:**
    <pre><code class="lang-bash">pip install -r requirements.txt</code></pre>

4.  **Run the Application:**
    <pre><code class="lang-bash">streamlit run app.py</code></pre>

---

## 🧠 Key Concepts

This dashboard is built around several key concepts from modern Quality Management Systems (QMS) and project management:

| Acronym   | Concept                               | Description                                                                                                        |
| --------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **RBQM**  | Risk-Based Quality Management         | An approach that focuses QA resources on the most critical risks to patient safety and data integrity.               |
| **SPC**   | Statistical Process Control           | A method for monitoring, controlling, and improving a process through statistical analysis.                          |
| **CAPA**  | Corrective and Preventive Action      | A systematic process for investigating and correcting discrepancies to prevent their recurrence.                       |
| **CPI/SPI** | Cost/Schedule Performance Index       | Metrics from Earned Value Management to assess project health. A value > 1.0 is favorable.                         |
| **GCP**   | Good Clinical Practice                | An international ethical and scientific quality standard for designing, conducting, and reporting clinical trials.     |

---
