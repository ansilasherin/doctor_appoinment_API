"""
Seed script — populates the DB with demo doctors, patients, and appointments.
Run: python seed.py
Requires .env to be configured with a valid DATABASE_URL.
"""
import os
import sys
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal, engine, Base
import app.models  # noqa — ensure all models registered

from app.models.user import User, UserRole
from app.models.doctor import Doctor, DoctorSchedule, Specialty
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("Seeding database...")

# ── Admin ──────────────────────────────────────────────────────────────────
if not db.query(User).filter(User.email == "admin@feelgood.com").first():
    admin = User(
        name="Admin User",
        email="admin@feelgood.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.admin,
    )
    db.add(admin)
    db.flush()
    print("  Created admin")

# ── Demo patients ──────────────────────────────────────────────────────────
patients_data = [
    ("Priya Sharma", "priya@example.com", "+919876543210"),
    ("Rahul Verma", "rahul@example.com", "+919876543211"),
    ("Anjali Singh", "anjali@example.com", "+919876543212"),
]
patients = []
for name, email, phone in patients_data:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(name=name, email=email, phone=phone,
                 hashed_password=hash_password("patient123"), role=UserRole.patient)
        db.add(u)
        db.flush()
        print(f"  Created patient: {name}")
    patients.append(u)

# ── Demo doctors ───────────────────────────────────────────────────────────
doctors_data = [
    {
        "name": "Dr. Arun Kumar", "email": "arun@feelgood.com", "phone": "+919000000001",
        "specialty": Specialty.dentist, "experience_years": 10, "consultation_fee": 500,
        "bio": "Dr. Arun Kumar is a highly skilled dentist with over 10 years of experience in dental care. Specializes in cosmetic dentistry and root canal treatments.",
        "clinic_name": "Arun Dental Clinic", "clinic_city": "Chennai", "qualification": "BDS, MDS",
        "avg_consultation_minutes": 30,
    },
    {
        "name": "Dr. Meera Iyer", "email": "meera@feelgood.com", "phone": "+919000000002",
        "specialty": Specialty.cardiologist, "experience_years": 15, "consultation_fee": 800,
        "bio": "Dr. Meera Iyer is an experienced cardiologist specializing in preventive cardiology and heart failure management.",
        "clinic_name": "Heart Care Center", "clinic_city": "Chennai", "qualification": "MBBS, MD, DM Cardiology",
        "avg_consultation_minutes": 30,
    },
    {
        "name": "Dr. Suresh Nair", "email": "suresh@feelgood.com", "phone": "+919000000003",
        "specialty": Specialty.dermatologist, "experience_years": 8, "consultation_fee": 600,
        "bio": "Expert dermatologist specializing in acne, pigmentation, and cosmetic skin treatments.",
        "clinic_name": "Skin & Glow Clinic", "clinic_city": "Chennai", "qualification": "MBBS, MD Dermatology",
        "avg_consultation_minutes": 20,
    },
    {
        "name": "Dr. Lakshmi Reddy", "email": "lakshmi@feelgood.com", "phone": "+919000000004",
        "specialty": Specialty.pediatrician, "experience_years": 12, "consultation_fee": 450,
        "bio": "Caring pediatrician with expertise in newborn care, vaccinations, and child development.",
        "clinic_name": "Little Stars Clinic", "clinic_city": "Bangalore", "qualification": "MBBS, MD Pediatrics",
        "avg_consultation_minutes": 25,
    },
    {
        "name": "Dr. Vikram Joshi", "email": "vikram@feelgood.com", "phone": "+919000000005",
        "specialty": Specialty.neurologist, "experience_years": 18, "consultation_fee": 1000,
        "bio": "Senior neurologist with expertise in epilepsy, stroke, and neurodegenerative diseases.",
        "clinic_name": "Neuro Care Hospital", "clinic_city": "Mumbai", "qualification": "MBBS, MD, DM Neurology",
        "avg_consultation_minutes": 40,
    },
    {
        "name": "Dr. Ananya Das", "email": "ananya@feelgood.com", "phone": "+919000000006",
        "specialty": Specialty.orthopedic, "experience_years": 9, "consultation_fee": 700,
        "bio": "Orthopedic surgeon specializing in sports injuries, joint replacement, and spine disorders.",
        "clinic_name": "Bone & Joint Center", "clinic_city": "Delhi", "qualification": "MBBS, MS Orthopedics",
        "avg_consultation_minutes": 30,
    },
]

doctor_users = []
for d in doctors_data:
    u = db.query(User).filter(User.email == d["email"]).first()
    if not u:
        u = User(name=d["name"], email=d["email"], phone=d["phone"],
                 hashed_password=hash_password("doctor123"), role=UserRole.doctor)
        db.add(u)
        db.flush()
        print(f"  Created doctor user: {d['name']}")

    doc = db.query(Doctor).filter(Doctor.user_id == u.id).first()
    if not doc:
        doc = Doctor(
            user_id=u.id,
            specialty=d["specialty"],
            experience_years=d["experience_years"],
            consultation_fee=d["consultation_fee"],
            bio=d["bio"],
            clinic_name=d["clinic_name"],
            clinic_city=d["clinic_city"],
            qualification=d["qualification"],
            avg_consultation_minutes=d["avg_consultation_minutes"],
            rating=4.5,
            total_reviews=20,
        )
        db.add(doc)
        db.flush()

        # Mon-Fri 9am-5pm, Sat 9am-1pm
        for day in range(5):  # Mon-Fri
            db.add(DoctorSchedule(doctor_id=doc.id, day_of_week=day,
                                  start_time=time(9, 0), end_time=time(17, 0)))
        db.add(DoctorSchedule(doctor_id=doc.id, day_of_week=5,  # Sat
                              start_time=time(9, 0), end_time=time(13, 0)))
        print(f"  Created doctor profile + schedules: {d['name']}")

    doctor_users.append((u, doc))

db.commit()

# ── Sample appointments ────────────────────────────────────────────────────
import random, string

def gen_ref():
    return "FG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

if db.query(Appointment).count() == 0 and patients and doctor_users:
    tomorrow = date.today() + timedelta(days=1)
    appt = Appointment(
        patient_id=patients[0].id,
        doctor_id=doctor_users[0][1].id,
        appointment_date=tomorrow,
        start_time=time(10, 0),
        end_time=time(10, 30),
        status=AppointmentStatus.confirmed,
        appointment_type=AppointmentType.in_person,
        symptoms="Tooth pain",
        consultation_fee=500,
        booking_ref=gen_ref(),
        payment_status="pending",
    )
    db.add(appt)
    db.commit()
    print("  Created sample appointment")

print("\nSeed complete!")
print("\nTest credentials:")
print("  Admin:   admin@feelgood.com / admin123")
print("  Patient: priya@example.com / patient123")
print("  Doctor:  arun@feelgood.com / doctor123")
db.close()
