<p align="center">

# LogNomaly

### Explainable AI System for Log Anomaly Detection

AI-powered platform for detecting and explaining anomalies in large-scale system logs.

</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Machine Learning](https://img.shields.io/badge/ScikitLearn-ML-orange)
![ASP.NET](https://img.shields.io/badge/Web-ASP.NET%20Core-purple)
![License](https://img.shields.io/badge/License-MIT-green)

</p>

---

## Overview

LogNomaly is a hybrid anomaly detection platform designed for Security Operations Centers (SOC). It analyzes unstructured system logs using a combination of machine learning algorithms and explainable AI techniques. 

Going beyond static predictions, LogNomaly features a **Continuous Learning Loop**. It parses raw logs, detects anomalies using multiple models, and empowers analysts to review predictions through an interactive dashboard. Analyst feedback is then used to dynamically retrain and refine the AI pipeline, creating a true Human-in-the-Loop (HITL) security ecosystem.

---

## Architecture

<p align="center">

<img width="750" height="500" alt="image" src="https://github.com/user-attachments/assets/09d81663-61eb-491f-8fcc-07a870d571ed" />

</p>

### How It Works (The LogNomaly Pipeline):

**1. Data Ingestion & Preprocessing:** The system accepts both single log lines and bulk log files. Built-in NLP components automatically clean the raw logs, mask sensitive identifiers (like IP addresses), and extract crucial contextual data (such as temporal features via TF-IDF).

**2. Multi-Layer Threat Detection:** Processed logs are fed into a hybrid detection engine. A Rule Engine instantly flags known threats, while the Isolation Forest and Random Forest models detect zero-day anomalies and classify the threat type. Finally, Explainable AI (SHAP) generates a transparent breakdown of *why* the AI flagged the event.

**3. Human-in-the-Loop Triage:** Detected anomalies are sent to the SOC Dashboard. Junior and Senior analysts can claim cases, investigate the raw payload alongside AI explanations, and verify the threat. If the AI makes a mistake, analysts can label it as a False Positive or False Negative.

**4. Dynamic Retraining Loop:** Approved analyst corrections are pushed to the ML retraining pipeline via the Admin panel. The AI models safely retrain by combining these new corrections with baseline data to prevent catastrophic forgetting. The updated models are then hot-reloaded into the live system without any downtime.

---

## Key Features

**Advanced AI & Machine Learning Pipeline**
* **Hybrid Anomaly Detection:** Combines Isolation Forest, Random Forest, and a custom Rule Engine for high-accuracy threat hunting.
* **Continuous Learning (Human-in-the-Loop):** Automated ML retraining pipeline triggered by analyst feedback to prevent model drift.
* **Explainable AI (XAI):** Transparent decision-making using SHAP to provide clear context for every detected anomaly.
* **Automated Feature Extraction:** Built-in NLP processing for parsing and vectorizing raw system logs.

**Security Operations Center (SOC) Management**
* **Role-Based Access Control (RBAC):** Tailored interfaces and permissions for Junior Analysts, Senior Analysts, and Administrators.
* **Case Management & Triage:** Efficient workflow for assigning, investigating, and resolving security incidents.
* **FP/FN Feedback Mechanism:** Direct labeling of False Positives and False Negatives to improve future AI accuracy.

**Platform & Interface**
* **Interactive & Responsive Dashboard:** Real-time metrics, risk distributions, and log tracking optimized for both desktop and mobile devices.
* **Flexible Analysis Modes:** Supports both single-line log analysis and bulk log file processing.

---

## Tech Stack

| Layer          | Technology           |
| -------------- | -------------------- |
| ML Pipeline    | Python, Scikit-learn |
| API            | Flask                |
| Web Interface  | ASP.NET Core MVC     |
| Visualization  | HTML, CSS, JS        |
| Infrastructure | Docker               |

---

## Project Structure

```
LogNomaly
│
├── app/                # Python API
├── models/             # ML models
├── utils/              # log processing
├── data/               # log data for training
├── tests/              # unit tests
├── LogNomaly.Web/      # ASP.NET dashboard
└── saved_models/       # trained models
```

---

## Installation

### 1. Clone repository
First, clone the project to your local machine and navigate to the project directory:
```
git clone https://github.com/dogaece-koca/LogNomaly.git
cd LogNomaly
```

### 2. NuGet Package Installation (C# Backend)
After pulling the project, you need to restore the backend dependencies:

* Visual Studio: Open the solution and go to Build > Rebuild Solution. Visual Studio will automatically download and restore all necessary NuGet packages.

* CLI: Alternatively, you can run the following command in the project root:

```
dotnet restore
```

### 3. Database Configuration & Migrations (Crucial)
The project includes several tables and relationships (SOC assignments, Case roles, etc.).

1. Connection String: Open appsettings.json and ensure the ConnectionString (Username/Password) matches your local PostgreSQL configuration.

2. Apply Migrations: Open the Package Manager Console (PMC) in Visual Studio and run:

```
Update-Database
```

* CLI: Alternatively, you can run the following command in the project root:
```
dotnet ef database update
```

### 4. Python API & Dependency Setup
The ML/NLP component runs on a Flask API. Navigate to the Python directory, activate your virtual environment (optional but recommended), and install the dependencies:

```
pip install -r requirements.txt
```

### 5. ML Model Deployment
The API is designed to read models from a directory named saved_models in the root of the Python project.
1. Navigate to the pre-trained models in the Releases section of this repository.
2. Locate the saved_models.zip file.
3. Extract the contents of this zip file into a folder named saved_models inside the Python API directory.
   * Note: The system will throw a "Model not found" error if this folder is missing or incorrectly named.

---

## Datasets

The system log datasets (BGL and HDFS) used for training and evaluating the machine learning models in this project were obtained from **[LogHub](https://github.com/logpai/loghub)**. 

LogHub is a freely available collection of system log datasets maintained by LogPAI, specifically curated for AI-powered log analytics, anomaly detection, and research purposes. We would like to acknowledge and thank the creators and contributors of LogHub for providing these invaluable open-source resources to the academic community. The log datasets we used are as follows:

This project uses the **Blue Gene/L (BGL) log dataset**, a widely used benchmark for log anomaly detection research.

Download link: [🔗](https://zenodo.org/records/8196385/files/BGL.zip?download=1)

Place it inside:

```
data/BGL.log
```

This project uses the **Hadoop Distributed File System (HDFS) v1 log dataset**, a popular benchmark generated in a private cloud environment.

Download link: [🔗](https://zenodo.org/records/8196385/files/HDFS_v1.zip?download=1)

Place it inside:

```
data/HDFS.log
```

---

## Train the Models

Before running the training script, open `train.py` and set the `DATASET_MODE` variable to your target dataset (either `"BGL"` or `"HDFS"`). Once configured, execute the following command:

```
python train.py
```
---

## Pre-trained Models

Due to GitHub's file size limits, the trained machine learning models for LogNomaly are hosted via GitHub Releases rather than directly in the repository.

**To run the project locally:**
1. Navigate to the [Releases](../../releases) page of this repository.
2. Download the latest release asset (`saved_models.zip`).
3. Extract the contents and place the `.joblib` model files into your designated models directory (`/saved_models`).
4. Run the application.

---
   
## Run the API

```
python app/app.py
```

---

## Run the Web Dashboard

```
cd LogNomaly.Web
dotnet run
```

Open:

```
http://localhost:5000
```
(or a specific port assigned by your local environment)

---

## Authors

Doğa Ece Koca —
Computer Engineering Student at Dokuz Eylül University

Fatmagül Fırtına —
Computer Engineering Student at Dokuz Eylül University

---

## License

MIT License
