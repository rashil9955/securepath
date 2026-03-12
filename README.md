# SecurePath
<img width="1443" height="763" alt="Screenshot 2026-01-21 at 4 58 43 PM" src="https://github.com/user-attachments/assets/23e4f758-0023-492c-9ff7-c66966b0ec09" />


![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Django](https://img.shields.io/badge/Django-REST_Framework-092E20?logo=django)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql)
![Celery](https://img.shields.io/badge/Celery-Redis-37814A?logo=celery)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **A full-stack fraud detection platform** that ingests transaction data, runs ML-based anomaly detection, and surfaces risk scores through an interactive dashboard — built as an academic capstone project.

<!-- 📸 Add a screenshot: ![SecurePath Dashboard](docs/screenshot.png) -->

---

## What It Does

Upload a CSV of transactions or connect a live bank account via **Plaid**, and SecurePath automatically flags suspicious activity using a trained scikit-learn classifier. Results are visualized in a real-time dashboard with export options for reporting.

| Feature | Description |
|---|---|
| 📂 **CSV Upload** | Upload transaction logs and run batch fraud detection instantly |
| 🏦 **Plaid Integration** | Connect real bank accounts via Plaid sandbox API |
| 🤖 **ML Fraud Detection** | scikit-learn classifier scores each transaction by risk level |
| ⚡ **Async Processing** | Celery + Redis handle background ML jobs without blocking the UI |
| 📊 **Dashboard** | Visualize risk distributions, flagged transactions, and trends with Chart.js |
| 📤 **Export** | Download flagged transaction reports as CSV |

---

## Tech Stack

**Backend**
- [Django REST Framework](https://www.django-rest-framework.org/) — API layer
- [PostgreSQL](https://www.postgresql.org/) — production database (SQLite for dev)
- [scikit-learn](https://scikit-learn.org/) — fraud detection ML model
- [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) — async background task processing
- [Plaid API](https://plaid.com/docs/) — bank account data integration

**Frontend**
- [React 18](https://react.dev/) — component-based UI
- [TailwindCSS](https://tailwindcss.com/) — utility-first styling
- [Chart.js](https://www.chartjs.org/) — transaction risk visualizations

---

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # Add your keys (see Environment Variables)
python manage.py migrate
python manage.py runserver     # Runs on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm start                      # Runs on http://localhost:3000
```

### Background Worker (for async fraud detection)

```bash
# In a separate terminal
celery -A backend worker --loglevel=info
```

---

## Environment Variables

```env
# Django
SECRET_KEY=your_django_secret_key
DEBUG=True

# Database (leave blank to use SQLite for dev)
DATABASE_URL=postgresql://user:password@localhost:5432/securepath

# Plaid (get sandbox keys from plaid.com/docs/sandbox)
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Auth
API_TOKEN=your_api_token
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/dashboard/stats` | Dashboard summary stats |
| `POST` | `/api/v1/upload` | Upload CSV transaction file |
| `POST` | `/api/v1/detect-fraud` | Run fraud detection on transactions |
| `GET` | `/api/v1/export/csv` | Export flagged transactions |

All endpoints require `Authorization: Bearer <API_TOKEN>` header.

---

## Project Structure

```
securepath/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   └── api/               # Django app — models, views, ML pipeline
├── frontend/
│   ├── src/               # React components & Chart.js dashboards
│   └── package.json
├── test_data/             # Sample CSV files for testing
└── setup.sh               # One-command dev setup
```

---

## Roadmap

- [ ] Improved ML model with labeled training data
- [ ] Real-time transaction monitoring with WebSockets
- [ ] User authentication and multi-account support
- [ ] More visualization options (transaction timelines, geo maps)

---

## About

Built by [Manish Neupane](https://www.linkedin.com/in/manish-neupane-380a65189) as an academic capstone project at SDSU, bridging data science and full-stack web development. The project demonstrates end-to-end ML integration — from raw CSV ingestion through async processing to interactive risk visualization.
