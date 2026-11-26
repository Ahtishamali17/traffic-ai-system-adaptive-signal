# 🚦 Sentry — AI-Powered Intelligent Traffic Monitoring & Adaptive Signal System

> **A Deep Learning + NLP based intelligent traffic management system for real-time vehicle detection, tracking, violation monitoring, adaptive signal intelligence, traffic analytics, and automated complaint prioritization.**

Sentry combines **Computer Vision, Deep Learning, Natural Language Processing (NLP), and intelligent traffic analytics** into a single platform for modern traffic monitoring and management.

The system analyzes live or uploaded traffic footage to detect and track vehicles, estimate speed, identify violations, monitor traffic density, and generate analytics. It also includes an **NLP-powered Complaints Intelligence module** that understands English traffic complaints, classifies them into relevant categories, and automatically determines whether a complaint requires **Urgent** or **Normal** attention.

---

## 🧠 AI at the Core

Sentry contains two major AI pipelines:

### 1. 🚗 Computer Vision & Deep Learning

Traffic video is processed using:

- **YOLOv8 (Ultralytics)** — real-time vehicle detection
- **PyTorch** — deep learning framework
- **DeepSORT** — multi-object vehicle tracking
- **OpenCV** — video processing and computer vision
- Speed estimation and trajectory analysis
- Traffic density and heatmap generation
- Rule-based traffic violation detection

### 2. 🗣️ Natural Language Processing (NLP)

The **Complaints (NLP)** module processes English-language traffic complaints using:

- **TF-IDF** for text feature extraction
- **Logistic Regression** for complaint classification
- Safety-keyword based priority detection
- Automatic complaint categorization
- Urgent vs Normal priority classification

The NLP pipeline runs locally on the CPU and does not require a GPU, internet connection, or external API key for prediction.

---

## ✨ Key Features

### 🚘 Vehicle Detection

Detects vehicles from:

- Webcam
- CCTV/IP camera
- RTSP streams
- Dashcam footage
- Drone footage
- Uploaded videos

Supported vehicle classes include:

- Car
- Truck
- Bus
- Motorcycle
- Bicycle
- Auto-rickshaw
- Van
- Emergency vehicle

> Custom-trained models are required for some specialized vehicle classes.

### 🎯 Vehicle Tracking

DeepSORT provides persistent vehicle tracking with:

- Unique vehicle IDs
- Vehicle trajectories
- Object lifetime tracking
- Motion direction
- Entry/exit tracking
- Multi-object tracking

### 🚦 Adaptive Traffic Signal Intelligence

The system uses traffic information such as:

- Vehicle count
- Traffic density
- Lane congestion
- Peak traffic periods
- Direction-wise traffic flow

to support intelligent traffic signal decisions rather than relying only on fixed timing.

### ⚠️ Traffic Violation Detection

The system can identify:

- Wrong-direction driving
- Lane violations
- Red-light jumping
- Illegal U-turns
- No-parking violations
- Overspeeding

### 🗣️ NLP-Based Complaint Intelligence

Users can enter natural-language English traffic complaints, and the system automatically determines the complaint category.

#### Supported Categories

| Category | Example |
|---|---|
| 🚦 Traffic Congestion | Heavy traffic and vehicles are stuck |
| 💥 Accident | Two vehicles have crashed |
| 🚥 Signal Fault | Traffic signal is not working |
| 🅿️ Illegal Parking | Cars are parked illegally |
| 🏎️ Rash Driving | A vehicle is being driven dangerously |
| 🛣️ Road Damage | Road is damaged or has potholes |

### 🚨 Automatic Complaint Priority

The NLP module determines whether a complaint should be treated as **Urgent** or **Normal**.

Safety-related keywords include:

`injury`, `bleeding`, `ambulance`, `fire`, `trapped`, `open manhole`

Example:

> **Complaint:** "There is an accident near the signal and someone is bleeding."

**Category:** Accident  
**Priority:** 🔴 Urgent  
**Reason:** Safety keyword detected — `bleeding`

Negative statements such as:

> "No injuries and nobody is hurt."

do not trigger the safety-keyword priority rule.

---

## 🤖 NLP Pipeline

```text
English Traffic Complaint
          │
          ▼
     Text Processing
          │
          ▼
    TF-IDF Vectorization
          │
          ▼
   Logistic Regression
          │
          ▼
   Complaint Category
          │
          ▼
   Priority Analysis
          │
          ▼
   Safety Keyword Rules
          │
          ▼
    Urgent / Normal
```

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────────┐
                    │        SENTRY AI         │
                    │  Intelligent Traffic AI  │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
   Computer Vision Pipeline                  NLP Pipeline
              │                                     │
        YOLOv8 Detection                       Text Input
              │                                     │
        DeepSORT Tracking                      TF-IDF
              │                                     │
       Speed Estimation                   Logistic Regression
              │                                     │
      Violation Detection                      Category
              │                                     │
       Traffic Analytics                       Priority
              │                                     │
              └──────────────────┬──────────────────┘
                                 │
                                 ▼
                      Intelligent Dashboard
```

---

## 📊 Traffic Analytics

The dashboard provides:

- Hourly vehicle counts
- Daily traffic statistics
- Vehicle-class distribution
- Peak-hour detection
- Violation statistics
- Traffic-density heatmaps
- Camera/session analytics
- Historical traffic information

---

## 📈 Dashboard

The React dashboard provides a centralized traffic operations interface with:

- 🏠 Dashboard
- 🎥 Live Detection
- 📊 Analytics
- 🗣️ **Complaints (NLP)**
- 📄 Reports
- ⚙️ Settings
- ℹ️ About

The interface uses a dark **traffic operations room** style for monitoring traffic activity.

---

## 🔔 Alerts

Automated notifications can be configured for:

- Traffic violations
- Overspeeding
- Crowded areas
- Loitering
- Other configured traffic events

Supported alert channels:

- Telegram
- Email

---

## 📄 Reports

Traffic information can be exported as:

- CSV
- Excel
- PDF

Reports can include traffic counts, vehicle distribution, violations, and analytics.

---

## 🗂️ Project Structure

```text
traffic-ai-system-adaptive-signal/
│
├── backend/
│   ├── app/
│   │   ├── api/              # REST API routes
│   │   ├── core/             # Configuration, database, logging
│   │   ├── nlp/              # NLP complaint classification
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Detection, analytics, reports, alerts
│   │   ├── tracking/         # DeepSORT tracking
│   │   ├── violations/       # Violation detection
│   │   ├── utils/            # Utility functions
│   │   └── tests/            # Backend tests
│   │
│   ├── scripts/
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── api/              # Backend API client
│       ├── components/       # UI components
│       └── pages/
│           ├── Dashboard
│           ├── LiveDetection
│           ├── Analytics
│           ├── Complaints
│           ├── Reports
│           ├── Settings
│           └── About
│
├── deployment/
│   ├── docker/
│   └── nginx/
│
├── docs/
├── models/
│   └── weights/              # Model weights (not committed)
│
├── docker-compose.yml
└── .gitignore
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **AI / Deep Learning** | YOLOv8, PyTorch |
| **Computer Vision** | OpenCV |
| **Object Tracking** | DeepSORT |
| **NLP** | TF-IDF, Logistic Regression |
| **Backend** | FastAPI, Python |
| **Frontend** | React, Vite, TailwindCSS, Framer Motion |
| **Visualization** | Chart.js |
| **Database** | MongoDB |
| **Data Processing** | NumPy, Pandas |
| **Deployment** | Docker, Nginx |
| **Testing** | Pytest |
| **CI/CD** | GitHub Actions |

---

## 🚀 Quick Start

### Clone the Repository

```bash
git clone https://github.com/Ahtishamali17/traffic-ai-system-adaptive-signal.git
cd traffic-ai-system-adaptive-signal
```

### Backend Setup

```bash
cd backend
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment configuration:

```bash
copy .env.example .env
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend API:

`http://localhost:8000`

API documentation:

`http://localhost:8000/api/docs`

### Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend dashboard:

`http://localhost:5173`

---

## 🐳 Docker

For a full-stack Docker setup:

```bash
docker compose up --build
```

This project includes Docker configuration for the backend and frontend, along with Nginx deployment configuration.

---

## 🧪 Testing

Backend tests can be executed using:

```bash
cd backend
PYTHONPATH=. pytest app/tests/ -v
```

The test suite covers major backend logic including:

- Vehicle-class mapping
- Drawing utilities
- Trajectory logic
- Line counting
- Speed calculation
- Violation detection
- Heatmap accumulation
- Report generation
- CSV/Excel/PDF generation

---

## 🔬 NLP Examples

### Example 1 — Accident

**Input:**
```text
There is a major accident near the signal. A person is bleeding and needs an ambulance.
```

**Output:**
```text
Category: Accident
Priority: Urgent
Reason: Safety keyword detected — bleeding
```

### Example 2 — Traffic Congestion

**Input:**
```text
There is heavy traffic near the main road and vehicles are stuck.
```

**Output:**
```text
Category: Traffic Congestion
Priority: Normal
```

### Example 3 — Signal Fault

**Input:**
```text
The traffic signal is not working at the intersection.
```

**Output:**
```text
Category: Signal Fault
Priority: Normal
```

---

## 🔐 Security & Configuration

Do not commit sensitive configuration to GitHub.

Keep values such as the following inside `.env`:

```text
DATABASE_URL
TELEGRAM_BOT_TOKEN
EMAIL_PASSWORD
SECRET_KEY
```

Model weights and large generated files should also be excluded from Git where appropriate.

---

## 📌 Project Status

### Completed

- ✅ YOLOv8 vehicle detection
- ✅ DeepSORT vehicle tracking
- ✅ Speed estimation
- ✅ Vehicle counting
- ✅ Traffic violation detection
- ✅ Traffic analytics
- ✅ Traffic-density heatmaps
- ✅ Adaptive traffic signal intelligence
- ✅ Multi-camera support
- ✅ Alert system
- ✅ CSV/Excel/PDF reports
- ✅ React dashboard
- ✅ NLP complaint classification
- ✅ TF-IDF feature extraction
- ✅ Logistic Regression classification
- ✅ Automatic complaint priority detection
- ✅ Backend testing
- ✅ Frontend production build
- ✅ Docker/deployment structure

---

## 🔮 Future Improvements

- Real-time adaptive signal control using reinforcement learning
- Advanced traffic prediction
- Multilingual complaint classification
- Transformer-based NLP models
- Automatic emergency response routing
- License plate recognition
- Real-time GIS/map integration
- Advanced anomaly detection
- Large-scale multi-camera traffic intelligence

---

## 👨‍💻 Author

**Ahtisham Ali**

GitHub: [@Ahtishamali17](https://github.com/Ahtishamali17)

---

## ⭐ Project Vision

Sentry brings together **Deep Learning + Computer Vision + NLP + Traffic Analytics** into one intelligent traffic management platform.

The system doesn't only understand **what is happening on the road through video**, but also understands **what people are reporting through natural language**.

> **See the traffic. Understand the complaint. Detect the problem. Prioritize the response.**
