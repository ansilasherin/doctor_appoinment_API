# FeelGood Appointments — Backend API

Python + FastAPI backend for the [FeelGood Appointments](https://feelgood-appointments.lovable.app) doctor booking platform.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111 |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL (Render free tier) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Migrations | Alembic |
| Email | aiosmtplib (Gmail / Brevo SMTP) |
| Hosting | Render (free web service + free PostgreSQL) |

---

## Project Structure

```
feelgood-backend/
├── app/
│   ├── main.py                  # FastAPI app entry point, CORS, router registration
│   ├── core/
│   │   ├── config.py            # Pydantic-settings env config
│   │   ├── database.py          # SQLAlchemy engine, session, Base
│   │   └── security.py          # JWT creation/decode, password hashing, auth dependencies
│   ├── models/
│   │   ├── __init__.py          # Imports all models (required for Alembic autogenerate)
│   │   ├── user.py              # User model (patient / doctor / admin roles)
│   │   ├── doctor.py            # Doctor profile + DoctorSchedule (weekly availability)
│   │   ├── appointment.py       # Appointment model
│   │   └── notification.py      # Review + Notification models
│   ├── schemas/
│   │   ├── auth.py              # Register, Login, Token request/response schemas
│   │   ├── user.py              # User CRUD schemas
│   │   ├── doctor.py            # Doctor + Schedule + Slot schemas
│   │   ├── appointment.py       # Appointment create/update/out schemas
│   │   └── review.py            # Review + Notification schemas
│   ├── routers/
│   │   ├── auth.py              # /api/v1/auth/*
│   │   ├── users.py             # /api/v1/users/*
│   │   ├── doctors.py           # /api/v1/doctors/*
│   │   ├── appointments.py      # /api/v1/appointments/*
│   │   ├── reviews.py           # /api/v1/reviews/*
│   │   ├── notifications.py     # /api/v1/notifications/*
│   │   └── admin.py             # /api/v1/admin/*
│   └── services/
│       └── email_service.py     # Async SMTP email (confirmation, cancellation, reminder)
├── alembic/
│   ├── env.py                   # Alembic migration environment
│   ├── script.py.mako           # Migration file template
│   └── versions/                # Auto-generated migration files
├── alembic.ini                  # Alembic configuration
├── seed.py                      # Demo data seed script
├── requirements.txt
├── render.yaml                  # One-click Render deployment config
├── .env.example                 # Environment variable template
└── .gitignore
```

---

## API Endpoints

Base URL (local): `http://localhost:8000/api/v1`
Base URL (Render): `https://<your-service>.onrender.com/api/v1`

Interactive docs: `GET /docs` (Swagger UI) | `GET /redoc`

---

### Authentication  `/api/v1/auth`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | None | Register new user (patient/doctor) |
| POST | `/auth/login` | None | Login with email or phone + password |
| POST | `/auth/refresh` | None | Refresh access token using refresh token |
| POST | `/auth/change-password` | Bearer | Change own password |

**Register body:**
```json
{
  "name": "Priya Sharma",
  "email": "priya@example.com",
  "phone": "+919876543210",
  "password": "securepass",
  "role": "patient"
}
```
`role` can be `"patient"` | `"doctor"` | `"admin"`

**Login body:**
```json
{ "identifier": "priya@example.com", "password": "securepass" }
```

**Token response:**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "user_id": 1,
  "role": "patient",
  "name": "Priya Sharma"
}
```

---

### Users  `/api/v1/users`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | Bearer | Get own profile (includes doctor_profile if doctor) |
| PUT | `/users/me` | Bearer | Update own profile (name, email, phone, avatar_url) |
| GET | `/users/{user_id}` | Admin | Get any user by ID |
| DELETE | `/users/{user_id}` | Admin | Deactivate a user |

---

### Doctors  `/api/v1/doctors`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/doctors` | None | List/search doctors |
| GET | `/doctors/specialties` | None | List all specialties |
| GET | `/doctors/{id}` | None | Get doctor detail with schedules |
| POST | `/doctors` | Doctor/Admin | Create doctor profile |
| PUT | `/doctors/{id}` | Doctor/Admin | Update doctor profile |
| POST | `/doctors/{id}/schedules` | Doctor/Admin | Add weekly schedule slot |
| DELETE | `/doctors/{id}/schedules/{sid}` | Doctor/Admin | Remove a schedule slot |
| GET | `/doctors/{id}/slots?date=YYYY-MM-DD` | None | Get available booking slots for a date |

**List doctors query params:**
- `specialty` — filter by specialty enum value
- `city` — partial city name match
- `search` — search doctor name or clinic name
- `min_rating` — minimum rating (float)
- `max_fee` — maximum consultation fee
- `available_only=true` — only show available doctors
- `skip` / `limit` — pagination

**Specialties enum values:**
`Cardiologist`, `Dentist`, `Dermatologist`, `Neurologist`, `Orthopedic`, `Pediatrician`, `General Physician`, `Gynecologist`, `Ophthalmologist`, `Psychiatrist`, `ENT Specialist`, `Urologist`

**Slots response:**
```json
{
  "date": "2025-03-10",
  "doctor_id": 1,
  "slots": [
    { "start_time": "09:00", "end_time": "09:30", "is_available": true },
    { "start_time": "09:30", "end_time": "10:00", "is_available": false }
  ]
}
```

---

### Appointments  `/api/v1/appointments`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/appointments` | Patient | Book a new appointment |
| GET | `/appointments` | Bearer | List own appointments (filtered by role) |
| GET | `/appointments/{id}` | Bearer | Get appointment detail |
| PUT | `/appointments/{id}` | Doctor/Admin | Update appointment (notes, status, payment) |
| POST | `/appointments/{id}/cancel` | Bearer | Cancel an appointment |

**Book appointment body:**
```json
{
  "doctor_id": 1,
  "appointment_date": "2025-03-10",
  "start_time": "09:00",
  "appointment_type": "in_person",
  "symptoms": "Tooth pain on left side"
}
```

**List appointments query params:**
- `status` — filter by status: `pending`, `confirmed`, `cancelled`, `completed`, `no_show`
- `upcoming_only=true` — only future appointments
- `skip` / `limit` — pagination

**Appointment out includes:** `booking_ref`, `doctor_name`, `doctor_specialty`, `patient_name`

---

### Reviews  `/api/v1/reviews`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/reviews` | Patient | Submit a review for a completed appointment |
| GET | `/reviews/doctor/{doctor_id}` | None | Get all reviews for a doctor |

**Review body:**
```json
{
  "appointment_id": 1,
  "rating": 4.5,
  "comment": "Very professional and thorough examination."
}
```

Submitting a review auto-recalculates the doctor's `rating` and `total_reviews`.

---

### Notifications  `/api/v1/notifications`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notifications` | Bearer | List own notifications |
| GET | `/notifications/unread-count` | Bearer | Get unread notification count |
| POST | `/notifications/mark-read` | Bearer | Mark specific notifications as read |
| POST | `/notifications/mark-all-read` | Bearer | Mark all notifications as read |

**List query params:**
- `unread_only=true` — only unread
- `skip` / `limit` — pagination

---

### Admin  `/api/v1/admin`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/stats` | Admin | Platform statistics (users, appointments, revenue) |
| GET | `/admin/users` | Admin | List all users |
| POST | `/admin/appointments/{id}/complete` | Admin/Doctor | Mark appointment as completed |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-32+-char-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (optional — app works without it, just logs warnings)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your@gmail.com

# CORS
CORS_ORIGINS=http://localhost:3000,https://feelgood-appointments.lovable.app
```

---

## Local Development Setup

```bash
# 1. Clone and enter
git clone <repo-url>
cd feelgood-backend

# 2. Create virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up env
cp .env.example .env
# Edit .env with your DATABASE_URL (local PostgreSQL or Render)

# 5. Run migrations (or let startup auto-create tables)
alembic upgrade head

# 6. Seed demo data
python seed.py

# 7. Start server
uvicorn app.main:app --reload --port 8000
```

Visit: http://localhost:8000/docs

---

## Deploy to Render (Free Tier)

### Option A — One-click via render.yaml
1. Push code to GitHub
2. In Render dashboard → **New → Blueprint**
3. Connect GitHub repo → Render reads `render.yaml` and creates:
   - Free PostgreSQL database (`feelgood-db`)
   - Web service (`feelgood-backend`)
4. Add remaining env vars (SMTP, CORS) in Render dashboard
5. After deploy: `https://<service>.onrender.com/docs`

### Option B — Manual
1. Create a free **PostgreSQL** database on Render → copy the **External Connection String**
2. Create a new **Web Service** → connect GitHub repo
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add env vars: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, etc.
4. Deploy

> **Note:** Render free PostgreSQL databases expire after 90 days. Upgrade or re-create to keep data.

### Post-deploy: seed demo data
```bash
# Set DATABASE_URL to Render's external connection string
DATABASE_URL=<render-external-url> python seed.py
```

---

## Frontend Integration Notes

### Auth flow
1. Call `POST /api/v1/auth/login` → store `access_token` and `refresh_token`
2. Add header to all authenticated requests: `Authorization: Bearer <access_token>`
3. On 401 response, call `POST /api/v1/auth/refresh` with `refresh_token` to get new tokens

### Booking flow
1. `GET /api/v1/doctors?specialty=Dentist` — search doctors
2. `GET /api/v1/doctors/{id}` — show doctor profile page (matches app design)
3. `GET /api/v1/doctors/{id}/slots?date=2025-03-10` — show available time slots
4. `POST /api/v1/appointments` — book selected slot
5. `GET /api/v1/appointments` — show user's appointment history

### Dashboard stats
- `GET /api/v1/appointments?upcoming_only=true` → count for "Appointments" stat
- Doctor and clinic counts: use `GET /api/v1/doctors` total (or hardcode from admin stats)

---

## Demo Credentials (after running seed.py)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@feelgood.com | admin123 |
| Patient | priya@example.com | patient123 |
| Doctor | arun@feelgood.com | doctor123 |

---

## Free Resources Used

| Resource | Provider | Free Tier |
|---|---|---|
| PostgreSQL database | Render | 1 GB storage, 90-day expiry |
| Web hosting | Render | 512 MB RAM, sleeps after 15 min inactivity |
| Email SMTP | Gmail App Password | Free, ~500/day |
| Email SMTP (alt) | Brevo (formerly Sendinblue) | 300 emails/day free |
