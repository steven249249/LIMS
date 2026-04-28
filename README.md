# LIMS - Semiconductor FAB Relay Management System

A professional Laboratory Information Management System (LIMS) tailored for high-tech semiconductor FAB environments, featuring a multi-stage "Relay" architecture for cross-departmental experiment workflows.

## 🚀 Key Features

- **Relay Workflow Architecture**: Predefined experiment packages (Photo, Process, QC) that move seamlessly through specialized laboratories.
- **Premium Interactive Timeline**: A real-time visualization of equipment occupancy with 72px high-density rows, glassmorphism aesthetics, and "Active Now" indicators.
- **Bidirectional Schedule Sync**: Real-time synchronization between timeline booking adjustments and task execution lists.
- **Time-Locked Completion**: Functional safety locks that prevent lab members from completing tasks before their scheduled start time.
- **Dynamic Equipment Release**: Automatic recalculation of equipment availability the moment a task is marked as "Done".
- **Departmental Access Control**: Role-based access for Requesters, Lab Managers, and Lab Members with strict data isolation per laboratory.

## 🛠 Tech Stack

- **Backend**: Django & Django REST Framework (Python 3.10+)
- **Frontend**: Vue 3 (Vite 6, Pinia, Vue Router)
- **Database**: Supports MySQL and SQLite
- **Styling**: Vanilla CSS with modern premium design tokens

## 📦 Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher (v25 recommended)
- Git

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 👥 User Roles

- **Requester**: Creates experiment orders by selecting from predefined relay packages. Tracks progress through the "Order History" view.
- **Lab Manager**: Oversees their department's stage of the relay. Responsible for equipment allocation, personnel assignment, and schedule adjustments via the interactive timeline.
- **Lab Member**: Executes assigned tasks within their scheduled window. Marks tasks as complete to trigger the relay to the next laboratory.

## 📝 License

Distributed under the MIT License.

---
*Developed with precision for semiconductor FAB excellence.*
