# DataTrace AI

**AI-Powered Data Quality Monitoring, Anomaly Detection & Root Cause Analysis Platform**

DataTrace AI is an intelligent data quality and observability platform designed to automatically analyze datasets, detect data quality issues and anomalies, identify possible root causes, and provide AI-powered explanations in a user-friendly dashboard.

The system combines **data profiling, quality checks, anomaly detection, pipeline monitoring, and Generative AI** to help users understand the health of their data without manually inspecting large datasets.

---

## 🚀 Features

### 📊 Data Quality Analysis
- Automatically profiles uploaded datasets.
- Calculates important data quality metrics.
- Detects missing values and duplicate records.
- Identifies invalid and inconsistent data.
- Provides an overall data quality assessment.

### 🔍 Anomaly Detection
DataTrace detects various types of anomalies, including:

- Missing values
- Duplicate records
- Invalid values
- Outliers
- Inconsistent formats
- Unexpected data distributions
- Schema-related issues

### 🤖 AI-Powered Data Analysis

The platform provides an **Ask DataTrace** feature where users can ask natural-language questions about their datasets.

Example:

> "Summarize the data quality of this dataset. Explain the major anomalies and their possible root causes."

The AI analyzes the dataset's quality information and generates an understandable explanation of the detected issues and their possible causes.

### 🧩 Root Cause Analysis

DataTrace AI goes beyond simply reporting errors.

It attempts to explain:

- What went wrong?
- Which column or data area is affected?
- How serious is the issue?
- What could have caused it?
- What should be investigated or corrected?

### 🔄 Pipeline Monitoring

The system provides visibility into data processing and pipeline executions, including:

- Pipeline status
- Execution information
- Processing results
- Data quality outcomes
- Failed or problematic executions

### 📁 Dataset Management

Users can:

- Upload datasets
- View available datasets
- Inspect dataset information
- Analyze data quality
- Ask questions about datasets

### 📈 Interactive Dashboard

The frontend provides a centralized dashboard for monitoring:

- Dataset health
- Data quality scores
- Anomalies
- Pipeline executions
- AI-generated insights

---

# 🏗️ System Architecture

DataTrace AI follows a full-stack architecture:

```text
                    ┌───────────────────────┐
                    │       User            │
                    └──────────┬────────────┘
                               │
                               ▼
                    ┌───────────────────────┐
                    │   React Frontend      │
                    │   Interactive UI       │
                    └──────────┬────────────┘
                               │ REST API
                               ▼
                    ┌───────────────────────┐
                    │    FastAPI Backend    │
                    │                       │
                    │ Dataset Management    │
                    │ Quality Analysis      │
                    │ Anomaly Detection     │
                    │ Pipeline Monitoring   │
                    │ Ask DataTrace API     │
                    └──────────┬────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌────────────┐ ┌─────────────┐ ┌──────────────┐
        │ Database   │ │ Data Quality │ │ AI Service   │
        │            │ │ Engine       │ │              │
        └────────────┘ └─────────────┘ └──────┬───────┘
                                               │
                                               ▼
                                      ┌────────────────┐
                                      │ Local LLM /    │
                                      │ AI Model       │
                                      └────────────────┘
```

---

# 🛠️ Technology Stack

## Frontend

- **React.js**
- **Vite**
- **JavaScript**
- **Axios**
- **Lucide React**
- CSS

## Backend

- **Python**
- **FastAPI**
- **Pandas**
- REST APIs
- Data validation and processing

## Database

- Relational database for storing:

  - Dataset information
  - Data quality results
  - Anomalies
  - Pipeline executions
  - Analysis results

## AI

- **Ollama**
- Local Large Language Model
- AI-powered natural-language data analysis
- Root cause explanation

---

# 📂 Project Structure

```text
DataTrace/
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   └── ask_service.py
│   │   ├── ...
│   │   └── ...
│   │
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── DatabaseConnections.jsx
│   │   └── index.css
│   │
│   ├── package.json
│   └── ...
│
├── datasets/
│   └── sample datasets
│
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd DataTrace
```

---

# 🐍 Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 🤖 AI Model Setup

DataTrace AI can use a locally running Ollama model for AI-powered dataset analysis.

Install Ollama and make sure the required model is available.

Example:

```bash
ollama list
```

If the configured model is not available, pull it using the appropriate Ollama command.

The backend uses environment variables such as:

```text
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
```

> If Ollama is not required for the non-AI parts of the application, the dashboard and data-quality functionality can still be used independently of the AI question-answering feature.

---

# ▶️ Running the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The backend will normally be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 💻 Running the Frontend

Open another terminal and navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will display a local development URL, typically:

```text
http://localhost:5173
```

Open the URL in your browser.

---

# 🔎 Ask DataTrace

One of the main features of the project is the **Ask DataTrace** interface.

Users can ask questions such as:

```text
Summarize the data quality of this dataset.
Explain the major anomalies and their possible root causes.
```

The system processes the question together with relevant dataset quality information and sends the context to the AI service.

The AI then generates an explanation containing:

- Overall data quality
- Major issues
- Affected fields
- Possible root causes
- Recommendations for investigation

---

# 🧪 Testing

The project was tested using sample datasets containing different data-quality problems.

Testing includes:

### Dataset Testing

- Missing values
- Duplicate records
- Invalid values
- Outliers
- Inconsistent data
- Quality-score calculation

### Backend Testing

- API endpoints
- Dataset processing
- Data-quality analysis
- Ask DataTrace API
- AI service integration

### Frontend Testing

- Dashboard rendering
- Dataset display
- Data-quality information
- Ask DataTrace interaction
- API communication

### AI Testing

The Ask DataTrace functionality was tested using questions such as:

```text
Summarize the data quality of this dataset.
Explain the major anomalies and their possible root causes.
```

The system successfully generated an AI-based explanation of the detected data-quality issues.

---

# 📌 Example Workflow

```text
1. User uploads dataset
          ↓
2. DataTrace reads the dataset
          ↓
3. Dataset profiling is performed
          ↓
4. Data quality checks are executed
          ↓
5. Anomalies are detected
          ↓
6. Quality results are stored
          ↓
7. User opens Ask DataTrace
          ↓
8. User asks a natural-language question
          ↓
9. Relevant dataset context is collected
          ↓
10. AI analyzes the context
          ↓
11. Explanation and possible root causes
    are returned to the user
```

---

# 🎯 Objectives

The main objectives of DataTrace AI are:

1. Automate data-quality assessment.
2. Detect data anomalies efficiently.
3. Reduce manual data inspection.
4. Provide understandable explanations of data issues.
5. Assist users in identifying possible root causes.
6. Provide centralized data observability.
7. Use Generative AI to make data-quality analysis accessible through natural language.

---

# 🌟 Advantages

- Automated data-quality monitoring
- Easy-to-use dashboard
- Natural-language interaction with datasets
- AI-assisted root cause analysis
- Local AI processing through Ollama
- Reduced manual investigation effort
- Centralized dataset and pipeline monitoring
- Extensible architecture

---

# 🔮 Future Scope

DataTrace AI can be extended with:

- Real-time data-quality monitoring
- Automated alerts and notifications
- More advanced anomaly-detection algorithms
- Data lineage visualization
- Automated data-quality remediation
- Support for additional databases and cloud platforms
- Role-based access control
- Historical quality trend analysis
- AI-generated data-quality reports
- Integration with enterprise data pipelines
- Automated root-cause correlation across pipeline stages

---

# 👩‍💻 Project

**Project Name:** DataTrace AI  
**Domain:** Data Engineering / Data Quality / Artificial Intelligence  
**Type:** Full-Stack AI-Based Data Observability Platform

---

# 📜 License

This project is developed for academic and educational purposes.

---

## 🙏 Acknowledgements

This project uses open-source technologies including:

- Python
- FastAPI
- React
- Vite
- Pandas
- Ollama
- JavaScript

---

## ⭐ Conclusion

**DataTrace AI** provides an intelligent approach to data-quality monitoring by combining automated quality analysis with Generative AI.

Instead of simply reporting that a dataset contains errors, DataTrace helps users understand **what went wrong, where the problem occurred, and what might have caused it**.

The project demonstrates how **Data Engineering + AI + Full-Stack Development** can be combined to build a practical data-observability solution.
