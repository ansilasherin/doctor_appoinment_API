import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str):
    """Send an HTML email. Silently logs errors so app doesn't crash if email fails."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not set — skipping email send")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")


async def send_appointment_confirmation(patient_email: str, patient_name: str, booking_ref: str,
                                         doctor_name: str, date: str, time: str, fee: float):
    subject = f"Appointment Confirmed — {booking_ref}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#3B82F6;padding:24px;border-radius:8px 8px 0 0">
        <h1 style="color:#fff;margin:0">FeelGood Appointments</h1>
      </div>
      <div style="padding:24px;background:#f9fafb;border-radius:0 0 8px 8px">
        <h2>Hi {patient_name}, your appointment is confirmed!</h2>
        <p><strong>Booking Reference:</strong> {booking_ref}</p>
        <p><strong>Doctor:</strong> {doctor_name}</p>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Time:</strong> {time}</p>
        <p><strong>Consultation Fee:</strong> ₹{fee:.0f}</p>
        <p style="color:#6b7280;font-size:14px">Please arrive 10 minutes early.</p>
      </div>
    </div>
    """
    await send_email(patient_email, subject, html)


async def send_appointment_cancellation(patient_email: str, patient_name: str, booking_ref: str,
                                          doctor_name: str, date: str):
    subject = f"Appointment Cancelled — {booking_ref}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#EF4444;padding:24px;border-radius:8px 8px 0 0">
        <h1 style="color:#fff;margin:0">FeelGood Appointments</h1>
      </div>
      <div style="padding:24px;background:#f9fafb;border-radius:0 0 8px 8px">
        <h2>Hi {patient_name}, your appointment has been cancelled.</h2>
        <p><strong>Booking Reference:</strong> {booking_ref}</p>
        <p><strong>Doctor:</strong> {doctor_name}</p>
        <p><strong>Date:</strong> {date}</p>
        <p>If you did not request this cancellation, please contact support.</p>
      </div>
    </div>
    """
    await send_email(patient_email, subject, html)


async def send_appointment_reminder(patient_email: str, patient_name: str, doctor_name: str,
                                     date: str, time: str, booking_ref: str):
    subject = f"Reminder: Appointment Tomorrow with {doctor_name}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#3B82F6;padding:24px;border-radius:8px 8px 0 0">
        <h1 style="color:#fff;margin:0">FeelGood Appointments</h1>
      </div>
      <div style="padding:24px;background:#f9fafb;border-radius:0 0 8px 8px">
        <h2>Reminder: You have an appointment tomorrow!</h2>
        <p><strong>Doctor:</strong> {doctor_name}</p>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Time:</strong> {time}</p>
        <p><strong>Booking Ref:</strong> {booking_ref}</p>
      </div>
    </div>
    """
    await send_email(patient_email, subject, html)
