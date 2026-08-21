from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
import smtplib
from email.message import EmailMessage
import hashlib
import secrets
import sqlite3
import requests
load_dotenv()
MAIL_ADDRESS = os.getenv("MAIL_ADDRESS")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
app = FastAPI()
current_email = None
camera_mail_sent = False
app.add_middleware(
    SessionMiddleware,
    secret_key="tir-takip-gizli-anahtar"
)
templates = Jinja2Templates(
    directory="templates"
)
def hash_password(password):
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    )
    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )
def verify_password(password, stored_password):
    salt_hex, hash_hex = stored_password.split(":")
    salt = bytes.fromhex(salt_hex)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    )
    return secrets.compare_digest(
        password_hash.hex(),
        hash_hex
    )
BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
DATABASE = os.path.join(
    BASE_DIR,
    "users.db"
)
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection
def send_email(to_email, subject, message):
    email = EmailMessage()
    email["From"] = MAIL_ADDRESS
    email["To"] = to_email
    email["Subject"] = subject
    email.set_content(message)
    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:
            smtp.login(
                MAIL_ADDRESS,
                MAIL_PASSWORD
            )
            smtp.send_message(email)
        print("MAIL GÖNDERİLDİ:", to_email)
        return True
    except Exception as e:
        print("MAIL GÖNDERİLEMEDİ:", e)
        return False
connection = get_db()
cursor = connection.cursor()
cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
connection.commit()
connection.close()
system_data = {
    "camera_connected": False,
    "truck_count": 0,
    "trucks": [],
    "reset": False
}
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )
@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    )
    user = cursor.fetchone()
    connection.close()
    if user is not None:
        password_correct = verify_password(
            password,
            user["password"]
        )
        if password_correct:
            global current_email
            current_email = user["email"]
            request.session["logged_in"] = True
            request.session["username"] = user["username"]
            request.session["email"] = user["email"]
            return RedirectResponse(
                url="/",
                status_code=303
            )
    return HTMLResponse(
        """
        <h2>Kullanıcı adı veya şifre hatalı.</h2>
        <a href="/login">
            Tekrar giriş yap
        </a>
        """,
        status_code=401
    )
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )
@app.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    connection = get_db()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        )
        existing_user = cursor.fetchone()
        if existing_user is not None:
            return HTMLResponse(
                """
                <h2>
                    Bu kullanıcı adı zaten kullanılıyor.
                </h2>
                <a href="/register">
                    Tekrar kayıt ol
                </a>
                """,
                status_code=400
            )
        hashed_password = hash_password(password)
        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                username,
                phone,
                email,
                password
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                username,
                phone,
                email,
                hashed_password
            )
        )
        connection.commit()
        print("KULLANICI KAYDEDİLDİ:")
        print("Kullanıcı adı:", username)
        print("Telefon:", phone)
    except Exception as e:
        connection.rollback()
        print("KULLANICI KAYDEDİLEMEDİ:", e)
        return HTMLResponse(
            f"""
            <h2>Kayıt sırasında hata oluştu.</h2>
            <p>{e}</p>
            <a href="/register">
                Tekrar dene
            </a>
            """,
            status_code=500
        )
    finally:
        connection.close()
    return RedirectResponse(
        url="/login",
        status_code=303
    )
@app.get("/logout")
async def logout(request: Request):
    global current_email
    request.session.clear()
    current_email = None
    return RedirectResponse(
        url="/login",
        status_code=303
    )
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse(
            url="/login",
            status_code=303
        )
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )
@app.post("/update")
async def update_data(data: dict):
    global system_data
    global camera_mail_sent
    system_data["camera_connected"] = data.get(
        "camera_connected",
        system_data["camera_connected"]
    )
    if data.get("reset") is True:
     system_data["trucks"] = []
     system_data["truck_count"] = 0
    incoming_trucks = data.get("trucks", [])
    for new_truck in incoming_trucks:
        if not any(
            old_truck["plate"] == new_truck["plate"]
            for old_truck in system_data["trucks"]
        ):
            system_data["trucks"].append(new_truck)
    system_data["truck_count"] = len(
        system_data["trucks"]
    )
    print("WEB'E VERİ GELDİ:")
    print(system_data)
    if data.get("camera_connected") is False:
     if not camera_mail_sent:
        if current_email is not None:
            print("MAIL GÖNDERİLİYOR:", current_email)
            send_email(
                current_email,
                "Tır Takip Sistemi - Kamera Bağlantısı",
                "UYARI: Tır takip sistemi kamera bağlantısını kaybetti. Kontrol ediniz."
            )
            camera_mail_sent = True
    else:
     camera_mail_sent = False
    return {
    "status": "ok"
    }
@app.post("/reset")
async def reset_system():
    global system_data
    system_data["trucks"] = []
    system_data["truck_count"] = 0
    system_data["reset"] = True
    return {
        "status": "ok"
    }
@app.post("/reset-complete")
async def reset_complete():
    global system_data
    system_data["reset"] = False
    return {
        "status": "ok"
    }
@app.get("/api/status")
async def get_status():
    return system_data