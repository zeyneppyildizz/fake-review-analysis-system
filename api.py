# ==========================================
# 1. KÜTÜPHANELER VE İÇE AKTARIMLAR (IMPORTS)
# ==========================================
import os
import time
import random
import smtplib
import sqlite3
import tempfile
import requests
import concurrent.futures
from typing import Optional
from fpdf import FPDF
from email.mime.text import MIMEText

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

import database
import scraper
import analyzer
import email_services 


# ==========================================
# 2. GÜVENLİK, SİSTEM AYARLARI VE YAPILANDIRMA
# ==========================================
CF_SECRET_KEY = "0x4AAAAAADOS72aVmMGjDyFloZmCjm9c2Eo"
GMAIL_SENDER = "emaililetim@gmail.com"        
GMAIL_PASSWORD = "rasd rslo mgjv hren"      

app = FastAPI(title="Radar AI API")

scheduler = BackgroundScheduler()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

database.init_db()


# ==========================================
# 3. GEÇİCİ BELLEK VE ÖNBELLEK (STATE/CACHE)
# ==========================================
verification_codes = {}  
registration_cache = {} 
reset_codes_db = {} 


# ==========================================
# 4. VERİ MODELLERİ (PYDANTIC SCHEMAS)
# ==========================================
class AuthRequest(BaseModel):
    username: str
    password: str
    cf_token: str 

class VerifyLoginRequest(BaseModel):
    username: str
    code: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    phone: str
    password: str
    cf_token: str 

class RegisterStep2Request(BaseModel):
    username: str
    code: str

class AnalyzeRequest(BaseModel):
    url: str
    username: str 

class UpdateProfileRequest(BaseModel):
    current_user: str
    email: str
    phone: str
    password: str = None

class AmazonUpdateRequest(BaseModel):
    username: str
    amazon_email: str
    amazon_password: str
    
class CompareRequest(BaseModel):
    url1: str
    url2: str
    username: str

class ContactRequest(BaseModel):
    name: str
    email: str
    message: str    

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str    

class TrackRequest(BaseModel):
    username: str
    url: str
    initial_score: float    

class AdminUserUpdateModel(BaseModel):
    admin_username: str  # İşlemi yapan adminin adı (Güvenlik için)
    email: Optional[str] = None
    phone: Optional[str] = None
    is_admin: bool = False


# ==========================================
# 5. YARDIMCI FONKSİYONLAR (UTILS & SMTP)
# ==========================================
def verify_turnstile(token: str):
    if not token:
        raise HTTPException(status_code=400, detail="Güvenlik doğrulaması (Captcha) eksik!")
    
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": CF_SECRET_KEY,
        "response": token
    }
    
    response = requests.post(url, data=data)
    result = response.json()
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Bot doğrulaması başarısız! Lütfen sayfayı yenileyip tekrar deneyin.")
    
def send_email_code(receiver_email: str, code: str):
    msg = MIMEText(f"Radar AI Sistemine Hoş Geldiniz.\n\nDoğrulama Kodunuz: {code}\n\nBu kod 3 dakika boyunca geçerlidir.", "plain", "utf-8")
    msg['Subject'] = 'Radar AI - Güvenlik Kodu'
    msg['From'] = f"Radar AI "
    msg['To'] = receiver_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() 
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Mail Gönderme Hatası:", e)
        return False
    
def send_contact_email(gonderen_ad: str, gonderen_email: str, mesaj: str):
    alici_email = "contact.radarai@gmail.com"
    
    mail_icerigi = f"""
Radar AI sisteminden yeni bir iletişim mesajı aldınız.

Gönderen: {gonderen_ad}
E-Posta: {gonderen_email}

Mesaj:
{mesaj}
"""
    msg = MIMEText(mail_icerigi, "plain", "utf-8")
    msg['Subject'] = f'Radar AI - Yeni İletişim Formu Mesajı ({gonderen_ad})'
    msg['From'] = f"Radar AI İletişim Sistemi"
    msg['To'] = alici_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() 
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, alici_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("İletişim Formu Mail Gönderme Hatası:", e)
        return False
    

# ==========================================
# 6. KİMLİK DOĞRULAMA ENDPOINTLERİ (AUTH)
# ==========================================
@app.post("/api/register-step1")
@limiter.limit("2/minute")
def register_step1(request: Request, req: RegisterRequest):
    verify_turnstile(req.cf_token)
    
    # 1. Kullanıcı adı zaten veritabanında var mı?
    existing_user = database.get_user_data(req.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış!")

    current_time = time.time()

    # 2. Spam Koruması
    if req.username in registration_cache:
        if registration_cache[req.username]["expires_at"] - current_time > 120:
            raise HTTPException(status_code=429, detail="Lütfen yeni kod istemeden önce 60 saniye bekleyin.")

    # 3. Kodu Üret ve Tüm Bilgileri Cache'e Al
    code = str(random.randint(100000, 999999))
    registration_cache[req.username] = {
        "email": req.email,
        "phone": req.phone,
        "password": req.password,
        "code": code,
        "expires_at": current_time + 180, 
        "attempts": 0
    }
    
    # 4. Maili Gönder
    success = send_email_code(req.email, code)
    if not success:
        raise HTTPException(status_code=500, detail="Mail gönderilemedi. Girdiğiniz e-posta adresini kontrol edin.")
        
    return {"status": "otp_sent", "message": f"Doğrulama kodu {req.email} adresine gönderildi."}

@app.post("/api/register-step2")
@limiter.limit("5/minute") 
def register_step2(request: Request, req: RegisterStep2Request):
    record = registration_cache.get(req.username)
    
    if not record:
        raise HTTPException(status_code=400, detail="Geçersiz işlem veya oturum zaman aşımı.")
        
    if time.time() > record["expires_at"]:
        del registration_cache[req.username] 
        raise HTTPException(status_code=400, detail="Kodun süresi dolmuş! Lütfen baştan kayıt olun.")
        
    if record["attempts"] >= 3:
        del registration_cache[req.username]
        raise HTTPException(status_code=403, detail="Çok fazla hatalı deneme! Güvenlik nedeniyle işlem iptal edildi.")
        
    if record["code"] != req.code:
        record["attempts"] += 1 
        raise HTTPException(status_code=400, detail=f"Hatalı kod! Kalan deneme hakkı: {3 - record['attempts']}")
        
    db_success = database.create_user(
        req.username, 
        record["email"], 
        record["phone"], 
        record["password"]
    )
    
    del registration_cache[req.username] 
    
    if db_success:
        return {"status": "success", "message": "E-posta doğrulandı ve kayıt başarılı!"}
    else:
        raise HTTPException(status_code=400, detail="Kayıt sırasında veritabanı hatası oluştu.")

@app.post("/api/login")
@limiter.limit("5/minute") 
def login(request: Request, req: AuthRequest):
    verify_turnstile(req.cf_token)
    
    # 1. Kullanıcı adı ve şifre kontrolü
    if not database.check_user(req.username, req.password):
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı veya şifre!")

    # 2. Şifre doğruysa kullanıcının e-postasını veritabanından çek
    user_data = database.get_user_data(req.username)
    if not user_data or not user_data.get("email"):
        raise HTTPException(status_code=400, detail="Bu kullanıcıya ait e-posta adresi bulunamadı.")
        
    user_email = user_data["email"]
    current_time = time.time()

    # 3. Spam Koruması 
    if req.username in verification_codes:
        if verification_codes[req.username]["expires_at"] - current_time > 120:
            raise HTTPException(status_code=429, detail="Lütfen yeni kod istemeden önce 60 saniye bekleyin.")

    # 4. Kodu Üret ve Kaydet
    code = str(random.randint(100000, 999999))
    verification_codes[req.username] = {
        "code": code,
        "expires_at": current_time + 180, 
        "attempts": 0
    }
    
    # 5. Maili Gönder
    success = send_email_code(user_email, code)
    if not success:
        raise HTTPException(status_code=500, detail="Mail gönderilemedi. Sistem loglarını kontrol edin.")
        
    at_index = user_email.find("@")
    masked_email = user_email[:2] + "***" + user_email[at_index:]
    
    return {"status": "otp_sent", "message": f"Doğrulama kodu {masked_email} adresine gönderildi."}

@app.post("/api/verify-login")
def verify_login(request: VerifyLoginRequest):
    record = verification_codes.get(request.username)
    
    if not record:
        raise HTTPException(status_code=400, detail="Geçersiz işlem veya oturum zaman aşımına uğradı.")
        
    if time.time() > record["expires_at"]:
        del verification_codes[request.username] 
        raise HTTPException(status_code=400, detail="Kodun süresi dolmuş! Lütfen baştan giriş yapın.")
        
    if record["attempts"] >= 3:
        del verification_codes[request.username]
        raise HTTPException(status_code=403, detail="Çok fazla hatalı deneme! Güvenlik nedeniyle işlem iptal edildi.")
        
    if record["code"] != request.code:
        record["attempts"] += 1 
        raise HTTPException(status_code=400, detail=f"Hatalı kod! Kalan deneme hakkı: {3 - record['attempts']}")
        
    del verification_codes[request.username]
    return {"status": "success", "message": "Giriş başarılı!"}

@app.post("/api/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest):
    reset_code = str(random.randint(100000, 999999))
    reset_codes_db[req.email] = reset_code
    
    mail_icerigi = f"""
Radar AI Şifre Sıfırlama Talebi

Şifrenizi sıfırlama kodunuz: {reset_code}

Eğer bu talebi siz yapmadıysanız bu mesajı görmezden gelebilirsiniz.
"""
    msg = MIMEText(mail_icerigi, "plain", "utf-8")
    msg['Subject'] = 'Radar AI - Şifre Sıfırlama Kodu'
    msg['From'] = GMAIL_SENDER      
    msg['To'] = req.email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, req.email, msg.as_string())
        server.quit()
        return {"message": "Şifre sıfırlama kodu e-posta adresinize gönderildi."}
    except Exception as e:
        print("Şifre sıfırlama mail hatası:", e)
        raise HTTPException(status_code=500, detail="Mail gönderilemedi.")

@app.post("/api/reset-password")
@limiter.limit("3/minute")
def reset_password(request: Request, req: ResetPasswordRequest):
    if req.email not in reset_codes_db or reset_codes_db[req.email] != req.code:
        raise HTTPException(status_code=400, detail="Hatalı veya süresi dolmuş kod.")
        
    basarili_mi = database.update_password_by_email(req.email, req.new_password)
    
    if not basarili_mi:
        raise HTTPException(status_code=404, detail="Bu e-posta adresiyle kesin eşleşen bir kayıt bulunamadı.")
        
    del reset_codes_db[req.email]
    
    return {"message": "Şifreniz başarıyla güncellendi! Yeni şifrenizle giriş yapabilirsiniz."}


# ==========================================
# 7. KULLANICI PROFİLİ VE YÖNETİM ENDPOINTLERİ
# ==========================================
@app.get("/api/user-info/{username}")
def get_info(username: str):
    data = database.get_user_data(username)
    if data: 
        return data
    raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

@app.post("/api/update-profile")
def update_profile(request: UpdateProfileRequest):
    success = database.update_user_profile(
        request.current_user, 
        request.email, 
        request.phone, 
        request.password
    )
    if success:
        return {"status": "success", "message": "Profil başarıyla güncellendi!"}
    raise HTTPException(status_code=400, detail="Güncelleme sırasında bir hata oluştu.")

@app.post("/api/update-amazon")
def update_amazon(request: AmazonUpdateRequest):
    success = database.update_amazon_credentials(request.username, request.amazon_email, request.amazon_password)
    if success:
        return {"status": "success", "message": "Amazon bilgileri veritabanına kaydedildi!"}
    raise HTTPException(status_code=400, detail="Amazon bilgileri kaydedilemedi.")

@app.delete("/api/users/{username}")
def delete_own_account(username: str):
    """Kullanıcının kendi hesabını sistemden kalıcı olarak siler."""
    if not username:
        raise HTTPException(status_code=400, detail="Kullanıcı adı gerekli.")
    
    basarili_mi = database.delete_user(username) 
    
    if basarili_mi:
        return {"status": "success", "message": "Hesabınız başarıyla silindi."}
    else:
        raise HTTPException(status_code=400, detail="Hesap silinemedi veya zaten yok.")


# ==========================================
# 8. ANALİZ VE RAPORLAMA (CORE API)
# ==========================================
@app.post("/api/analiz-et")
@limiter.limit("5/minute")
def analiz_et(request: Request, req: AnalyzeRequest):
    user_data = database.get_user_data(req.username)
    amz_email = user_data.get("amazon_email") if user_data else None
    amz_pass = user_data.get("amazon_password") if user_data else None

    yorumlar = scraper.get_amazon_reviews_auto(req.url, amz_email, amz_pass, max_sayfa=10)
    
    if not yorumlar:
        raise HTTPException(status_code=400, detail="Yorum bulunamadı veya bot engele takıldı.")
    
    sonuc = analyzer.perform_analysis(yorumlar)
    
    if not sonuc:
        raise HTTPException(status_code=500, detail="Model yüklenemedi.")
        
    ozet_klasoru = sonuc.get("ozet", {}) 
    risk_skoru = ozet_klasoru.get("sahtelik_orani", 0) 
    incelenen_yorum_sayisi = ozet_klasoru.get("toplam_yorum", len(yorumlar)) 
    
    database.save_analysis_result(
        username=req.username,        
        url=req.url,                    
        risk_score=risk_skoru,          
        comment_count=incelenen_yorum_sayisi 
    )
    return sonuc

@app.post("/api/kiyasla")
@limiter.limit("5/minute")
def urunleri_kiyasla(request: Request, req: CompareRequest):
    user_data = database.get_user_data(req.username)
    amz_email = user_data.get("amazon_email") if user_data else None
    amz_pass = user_data.get("amazon_password") if user_data else None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(scraper.get_amazon_reviews_auto, req.url1, amz_email, amz_pass, 10)
        future2 = executor.submit(scraper.get_amazon_reviews_auto, req.url2, amz_email, amz_pass, 10)

        yorumlar1 = future1.result()
        yorumlar2 = future2.result()

    if not yorumlar1 or not yorumlar2:
        raise HTTPException(status_code=400, detail="Ürünlerden birinin yorumları çekilemedi veya bot engele takıldı.")

    sonuc1 = analyzer.perform_analysis(yorumlar1)
    sonuc2 = analyzer.perform_analysis(yorumlar2)

    risk1 = sonuc1["ozet"]["sahtelik_orani"]
    risk2 = sonuc2["ozet"]["sahtelik_orani"]
    fark = abs(risk1 - risk2)

    if risk1 < risk2:
        if fark > 20:
            tavsiye = "1. Ürün açık ara daha güvenilir. 2. üründe ciddi sentetik/bot yorum manipülasyonu tespit edildi. Tercihiniz 1. Ürün olmalı."
        else:
            tavsiye = "1. Ürün organik yorum açısından biraz daha temiz, ancak iki ürün de benzer risk grubunda."
    elif risk2 < risk1:
        if fark > 20:
            tavsiye = "2. Ürün açık ara daha güvenilir. 1. ürünün yorumlarında aşırı şişirme mevcut. Tercihiniz 2. Ürün olmalı."
        else:
            tavsiye = "2. Ürün marjinal olarak daha dürüst yorumlara sahip görünüyor."
    else:
        tavsiye = "İki ürünün de yorum kalitesi ve sahtelik oranları birebir eşit düzeyde."

    return {
        "urun1": sonuc1,
        "urun2": sonuc2,
        "dss_karar": tavsiye
    }

@app.get("/api/export-pdf/{analysis_id}")
@limiter.limit("5/minute")
def export_analysis_pdf(request: Request, analysis_id: int):
    # 1. Veritabanından o ID'ye ait analizi çek
    data = database.get_analysis_by_id(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analiz bulunamadi.")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    
    # --- ÜST BAŞLIK ---
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 0, 0) 
    pdf.cell(0, 15, "RADAR AI - TEHDIT ANALIZ RAPORU", ln=True, align="C")
    
    pdf.set_draw_color(100, 100, 100)
    pdf.line(10, 25, 200, 25) # Çizgi çek
    pdf.ln(10)

    # --- VERİLER ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0) # Siyah
    
    # Tarih
    pdf.cell(50, 10, "Tarih / Saat:", border=0)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, str(data["created_at"]), border=0, ln=True)
    
    # URL
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(50, 10, "Hedef URL:", border=0)
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(0, 10, str(data["target_url"])) # Uzun linkler için multi_cell
    pdf.ln(2)

    # Yorum Sayısı
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(50, 10, "Incelenen Yorum:", border=0)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"{data['analyzed_comments_count']} Adet", border=0, ln=True)
    pdf.ln(10)

    # --- RİSK SKORU SONUCU ---
    risk_score = data["risk_score"]
    
    if risk_score > 50:
        durum_metni = "YUKSEK RISK (Sentetik / Bot Aktivitesi Tespit Edildi)"
        pdf.set_text_color(220, 53, 69) 
    else:
        durum_metni = "DUSUK RISK (Organik Aktivite)"
        pdf.set_text_color(40, 167, 69) 

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 15, f"RISK SKORU: %{risk_score} - {durum_metni}", ln=True, align="C", border=1)
    
    # --- ALT BİLGİ ---
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Bu rapor Radar AI sistemi tarafindan otomatik uretilmistir.", ln=True, align="C")
    pdf_bytes = pdf.output()
    
    headers = {
        "Content-Disposition": f"attachment; filename=RadarAI_Rapor_{analysis_id}.pdf"
    }
    
    return Response( 
        content=bytes(pdf_bytes), 
        media_type="application/pdf", 
        headers=headers
    )


# ==========================================
# 9. TAKİP (TRACKING), FAVORİLER VE İLETİŞİM
# ==========================================
@app.get("/api/analyses/history")
@limiter.limit("10/minute")
def get_history(request: Request, username: str = None): 
    # Not: Orijinal kodda aynı isimli iki fonksiyon bulunuyordu.
    # Bunların çakışmaması adına tek bir fonksiyonda username opsiyonel kontrol edildi.
    kullanici = username if username else "test_kullanicisi"
    
    if not kullanici:
        raise HTTPException(status_code=400, detail="Kullanıcı kimliği bulunamadı.")
        
    history = database.get_user_analyses(kullanici)
    return {"status": "success", "data": history}

@app.post("/api/track")
@limiter.limit("5/minute")
def add_to_tracking(request: Request, req: TrackRequest):
    conn = sqlite3.connect(database.DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM tracked_items WHERE username=? AND target_url=?", (req.username, req.url))
    zaten_var = c.fetchone()
    conn.close()
    
    if zaten_var:
        return {"status": "success", "message": "Zaten takipte."}
        
    basarili_mi = database.add_tracking(req.username, req.url, req.initial_score)
    if basarili_mi:
        return {"status": "success", "message": "Ürün radar takibine alındı."}
    else:
        raise HTTPException(status_code=400, detail="Sisteme eklenirken hata oluştu.")
    
@app.get("/api/check-tracking")
def check_tracking(username: str, url: str):
    conn = sqlite3.connect(database.DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM tracked_items WHERE username=? AND target_url=?", (username, url))
    sonuc = c.fetchone()
    conn.close()
    
    return {"is_tracked": bool(sonuc)}  

@app.get("/api/favorites")
def get_favorites(username: str):
    items = database.get_user_tracked_items(username)
    return {"status": "success", "data": items}

@app.delete("/api/favorites/{item_id}")
def remove_favorite(item_id: int):
    database.delete_tracked_item(item_id)
    return {"status": "success", "message": "Takipten çıkarıldı."}  

@app.post("/api/communication")
def contact(request: ContactRequest):
    gonderen_ad = request.name
    gonderen_email = request.email
    mesaj = request.message

    success = send_contact_email(gonderen_ad, gonderen_email, mesaj)
    if not success:
        raise HTTPException(status_code=500, detail="Mail gönderilemedi.")

    return {"status": "success", "message": "Mesaj başarıyla gönderildi."}


# ==========================================
# 10. ADMİN ENDPOINTLERİ
# ==========================================
@app.get("/api/admin/check")
def check_admin_status(username: str):
    """Arayüzde admin butonunu gösterip gizlemek için yetki kontrolü yapar."""
    if not username:
        return {"is_admin": False}
        
    is_admin = database.is_user_admin(username)
    return {"is_admin": is_admin}

@app.get("/api/admin/stats")
def get_admin_stats(username: str):
    """Admin paneli verilerini getirir. Güvenlik duvarı içerir."""
    if not username or not database.is_user_admin(username):
        raise HTTPException(status_code=403, detail="Yasak Bölge: Bu alana girmeye yetkiniz yok!")
    
    stats = database.get_admin_dashboard_stats()
    return {"status": "success", "data": stats}

@app.get("/api/admin/users")
def get_admin_users(username: str, q: Optional[str] = None):
    """Admin paneli için kullanıcı listesini getirir. Arama kutusunu (q) destekler."""
    if not username or not database.is_user_admin(username):
        raise HTTPException(status_code=403, detail="Yasak Bölge!")
    
    users = database.get_all_users(search_term=q)
    return {"status": "success", "data": users}

@app.put("/api/admin/users/{user_id}")
def update_user_from_admin(user_id: int, data: AdminUserUpdateModel):
    # 1. İşlemi yapan kişi gerçekten admin mi?
    if not database.is_user_admin(data.admin_username):
        raise HTTPException(status_code=403, detail="Yasak Bölge! Bu işlem için yetkiniz yok.")
        
    # 2. Güncellemeyi yap
    success = database.update_user_by_admin(user_id, data.email, data.phone, data.is_admin)
    if success:
        return {"status": "success", "message": "Kullanıcı başarıyla güncellendi."}
    else:
        raise HTTPException(status_code=400, detail="Kullanıcı güncellenemedi (Bulunamamış olabilir).")

@app.delete("/api/admin/users/{user_id}")
def delete_user_from_admin(user_id: int, admin_username: str):
    # 1. İşlemi yapan kişi gerçekten admin mi?
    if not database.is_user_admin(admin_username):
        raise HTTPException(status_code=403, detail="Yasak Bölge! Bu işlem için yetkiniz yok.")
        
    # 2. Silme işlemini yap
    success = database.delete_user_by_admin(user_id)
    if success:
        return {"status": "success", "message": "Kullanıcı sistemden tamamen silindi."}
    else:
        raise HTTPException(status_code=400, detail="Kullanıcı silinemedi.")
    
@app.get("/api/admin/logs")
def get_admin_logs(admin_username: str, target_username: str = None, target_date: str = None):
    # Güvenlik Kontrolü: İsteyen kişi admin mi?
    if not database.is_user_admin(admin_username):
        raise HTTPException(status_code=403, detail="Yasak Bölge! Logları görme yetkiniz yok.")
        
    # Veritabanından logları çek
    logs = database.get_global_analysis_history(username_filter=target_username, date_filter=target_date)
    return {"status": "success", "data": logs}    

@app.get("/api/admin/tracked_items")
def get_admin_tracked_items(admin_username: str, target_username: str = None):
    if not database.is_user_admin(admin_username):
        raise HTTPException(status_code=403, detail="Yetkisiz erisim!")
        
    items = database.get_all_tracked_items(username_filter=target_username)
    return {"status": "success", "data": items}

@app.get("/api/admin/export/users_pdf")
def export_users_pdf(admin_username: str):
    # 1. Güvenlik Kontrolü
    if not database.is_user_admin(admin_username):
        raise HTTPException(status_code=403, detail="Yetkisiz erisim!")
        
    # 2. Veritabanından kullanıcıları çek
    conn = sqlite3.connect(database.DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, email, phone, is_admin FROM users ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()

    # 3. FPDF ile PDF Tasarımı
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Radar AI - Sistem Kullanicilari Raporu", ln=True, align="C")
    pdf.ln(5)
    
    # Tablo Başlıkları
    pdf.set_font("Arial", "B", 10)
    pdf.cell(15, 10, "ID", border=1)
    pdf.cell(45, 10, "Kullanici Adi", border=1)
    pdf.cell(70, 10, "E-Posta", border=1)
    pdf.cell(35, 10, "Telefon", border=1)
    pdf.cell(25, 10, "Yetki", border=1, ln=True)
    
    # Tablo İçeriği
    pdf.set_font("Arial", "", 10)
    for r in rows:
        role = "Admin" if r["is_admin"] else "Kullanici"
        pdf.cell(15, 10, str(r["id"]), border=1)
        pdf.cell(45, 10, str(r["username"])[:20], border=1)
        pdf.cell(70, 10, str(r["email"] or "-")[:35], border=1)
        pdf.cell(35, 10, str(r["phone"] or "-")[:15], border=1)
        pdf.cell(25, 10, role, border=1, ln=True)
        
    # PDF'i belleğe kaydedip indirme olarak dön
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
    os.remove(tmp.name) # Geçici dosyayı temizle
        
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": "attachment; filename=RadarAI_Kullanicilar.pdf"}
    )

@app.get("/api/admin/export/logs_pdf")
def export_logs_pdf(admin_username: str, target_username: str = "", target_date: str = ""):
    # 1. Güvenlik Kontrolü
    if not database.is_user_admin(admin_username):
        raise HTTPException(status_code=403, detail="Yetkisiz erisim!")
        
    # 2. Verileri filtreli çekmek 
    logs = database.get_global_analysis_history(username_filter=target_username, date_filter=target_date)
    
    # 3. FPDF ile PDF Tasarımı
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Radar AI - Global Analiz Loglari", ln=True, align="C")
    
    # Kriter bilgisi yazdır
    filtre_metni = f"Filtreler -> Kullanici: {target_username or 'Hepsi'} | Tarih: {target_date or 'Hepsi'}"
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 10, filtre_metni, ln=True, align="C")
    pdf.ln(2)
    
    # Tablo Başlıkları
    pdf.set_font("Arial", "B", 9)
    pdf.cell(35, 10, "Tarih", border=1)
    pdf.cell(35, 10, "Kullanici", border=1)
    pdf.cell(100, 10, "Link", border=1)
    pdf.cell(20, 10, "Skor", border=1, ln=True)
    
    # Tablo İçeriği
    pdf.set_font("Arial", "", 8)
    for log in logs:
        short_url = log["url"][:55] + "..." if len(log["url"]) > 55 else log["url"]
        pdf.cell(35, 10, str(log["created_at"])[:16], border=1)
        pdf.cell(35, 10, str(log["username"])[:20], border=1)
        pdf.cell(100, 10, short_url, border=1)
        pdf.cell(20, 10, str(log["risk_score"]), border=1, ln=True)
        
    # PDF'i belleğe kaydedip indirme olarak dön
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
    os.remove(tmp.name) 
        
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": "attachment; filename=RadarAI_Loglar.pdf"}
    )

@app.get("/api/admin/export/tracked_pdf")
def export_tracked_pdf(admin_username: str, target_username: str = ""):
    if not database.is_user_admin(admin_username):
        raise HTTPException(status_code=403, detail="Yetkisiz erisim!")
        
    items = database.get_all_tracked_items(username_filter=target_username)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Radar AI - Aktif Takip Edilen Urunler", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(35, 10, "Kullanici", border=1)
    pdf.cell(100, 10, "Link", border=1)
    pdf.cell(20, 10, "Son Skor", border=1)
    pdf.cell(35, 10, "Son Kontrol", border=1, ln=True)
    
    pdf.set_font("Arial", "", 8)
    for item in items:
        short_url = str(item["url"])[:55] + "..." if len(str(item["url"])) > 55 else str(item["url"])
        pdf.cell(35, 10, str(item["username"])[:20], border=1)
        pdf.cell(100, 10, short_url, border=1)
        pdf.cell(20, 10, str(item["risk_score"]), border=1)
        pdf.cell(35, 10, str(item["last_checked_at"])[:16], border=1, ln=True)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
    os.remove(tmp.name) 
        
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": "attachment; filename=RadarAI_Takip_Edilenler.pdf"}
    )


# ==========================================
# 11. ARKA PLAN GÖREVLERİ (JOBS / SCHEDULER)
# ==========================================
def gece_bekcisi_taramasi():
    print("[SİSTEM] Gece Bekçisi Uyandı! Rutin taramalar başlıyor...")
    
    takipteki_urunler = database.get_all_tracked_items()
    
    for urun in takipteki_urunler:
        item_id = urun["id"]
        username = urun["username"]
        url = urun["target_url"]
        eski_skor = urun["last_risk_score"]
        
        try:
            user_data = database.get_user_data(username)
            amz_email = user_data.get("amazon_email") if user_data else None
            amz_pass = user_data.get("amazon_password") if user_data else None
            yorumlar = scraper.get_amazon_reviews_auto(url, amz_email, amz_pass, max_sayfa=10)

            if not yorumlar:
                continue 
                
            sonuc = analyzer.perform_analysis(yorumlar)
            if not sonuc:
                continue
                
            ozet_klasoru = sonuc.get("ozet", {})
            yeni_skor = ozet_klasoru.get("sahtelik_orani", sonuc.get("risk_score", 0))
            
            # KIYASLAMA VE ALARM MANTIĞI
            if yeni_skor >= (eski_skor + 10):
                print(f"[ALARM] {username} için {url} ürününde risk artışı! ({eski_skor} -> {yeni_skor})")
                kullanici_mail = user_data.get("email") 
                if kullanici_mail:
                    email_services.send_alert_email(kullanici_mail, url, eski_skor, yeni_skor)
            
            database.update_tracked_item_score(item_id, yeni_skor)
            
        except Exception as e:
            print(f"[HATA] Bekçi {url} linkini tararken takıldı: {e}")

    print("[SİSTEM] Gece Bekçisi devriyesini tamamladı ve uykuya döndü.")

@app.on_event("startup")
def start_background_jobs():
    scheduler.add_job(gece_bekcisi_taramasi, 'cron', hour=3, minute=0)
    scheduler.start()
    print("[SİSTEM] Bekçi zamanlayıcısı (Scheduler) başlatıldı.")

@app.on_event("shutdown")
def stop_background_jobs():
    scheduler.shutdown()
    print("[SİSTEM] Bekçi zamanlayıcısı durduruldu.")