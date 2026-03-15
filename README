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

LogNomaly is a hybrid anomaly detection platform that analyzes system logs using machine learning and explainable AI techniques.

The system parses raw logs, extracts features, detects anomalies using multiple models, and explains predictions through an interactive web dashboard.

---

## Architecture

<p align="center">

![architecture](docs/architecture.png)

</p>

Pipeline:

```
Raw Logs
   ↓
Log Parsing
   ↓
Feature Extraction
   ↓
Hybrid Detection Engine
   ↓
Explainable AI
   ↓
Web Dashboard
```

---

## Features

* Hybrid anomaly detection (Isolation Forest + Random Forest + Rule Engine)
* Explainable AI for anomaly interpretation
* Automated log feature extraction
* Interactive web-based dashboard
* Modular ML pipeline

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
├── training/           # training scripts
├── tests/              # unit tests
├── LogNomaly.Web/      # ASP.NET dashboard
└── docs/               # architecture diagrams
```

---

## Dataset

This project uses the **Blue Gene/L (BGL) log dataset**, a widely used benchmark for log anomaly detection research.

Download dataset from Kaggle:

https://www.kaggle.com/datasets/omduggineni/loghub-bgl-log-data

Place it inside:

```
data/BGL.log
```

---

## Installation

Clone repository

```
git clone https://github.com/dogaece-koca/LogNomaly.git
cd LogNomaly
```

Install dependencies

```
pip install -r requirements.txt
```

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

---

## Author

Doğa Ece Koca
Computer Engineering — Dokuz Eylül University

---

## License

MIT License
