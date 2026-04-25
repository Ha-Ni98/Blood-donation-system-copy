# 🩸 Blood Bank Management System — V2

> **V2** is the updated version of the Blood Bank Management System, located in the `V2/` folder.

---

## 🚀 Getting Started

Follow the steps below to set up and run the project locally.

### 1. Pull the Latest Changes

```bash
git pull origin
```

### 2. Navigate to the V2 Folder

```bash
cd V2
```

### 3. Apply Database Migrations

```bash
python manage.py migrate
```

### 4. Load Wilayas and Communes

```bash
python manage.py load_wilayas
```

### 5. Load Blood Types and Stock

```bash
python manage.py load_blood_data
```

### 6. Create an Admin Account

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

---

## 📋 Requirements

Make sure you have **Python** and **Django** installed before running the project.

---

## 📁 Project Structure

```
/
├── V2/        # Latest updated version
└── ...
```
