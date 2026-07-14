# ==========================================
# 1. KÜTÜPHANELER VE TEMEL AYARLAR
# ==========================================
import sqlite3
import hashlib
from cryptography.fernet import Fernet

DB_NAME = 'sistem_veritabani.db'

GIZLI_ANAHTAR = b'zQMGCwaEBbTpvwDo12EnQ7e13JkQQP1w9AsU6X01AhQ='
cipher_suite = Fernet(GIZLI_ANAHTAR)


# ==========================================
# 2. VERİTABANI BAŞLATMA VE TABLO OLUŞTURMA
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  email TEXT,
                  phone TEXT,
                  password_hash TEXT,
                  amazon_email TEXT,
                  amazon_password TEXT )''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass
                  
    c.execute('''CREATE TABLE IF NOT EXISTS analyses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  target_url TEXT,
                  risk_score REAL,
                  analyzed_comments_count INTEGER,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(username) REFERENCES users(username))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tracked_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  target_url TEXT,
                  last_risk_score REAL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  last_checked_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                      
    conn.commit()
    conn.close()


# ==========================================
# 3. ŞİFRELEME VE GÜVENLİK İŞLEMLERİ
# ==========================================
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def encrypt_amazon_pass(password: str):
    if not password: return password
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_amazon_pass(encrypted_password: str):
    if not encrypted_password: return encrypted_password
    try:
        return cipher_suite.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return encrypted_password


# ==========================================
# 4. KULLANICI YÖNETİMİ İŞLEMLERİ
# ==========================================
def create_user(username, email, phone, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, phone, password_hash) VALUES (?, ?, ?, ?)", 
                  (username, email, phone, hash_password(password)))
        conn.commit()
        return True 
    except sqlite3.IntegrityError:
        return False 
    finally:
        conn.close()

def check_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", 
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    
    return user is not None 

def get_user_data(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username, email, phone, amazon_email, amazon_password FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    if user:
        cozulmus_amazon_sifresi = decrypt_amazon_pass(user[4])
        return {"username": user[0], 
                "email": user[1], 
                "phone": user[2],
                "amazon_email": user[3],
                "amazon_password": cozulmus_amazon_sifresi}
    return None

def update_user_profile(old_username, new_email, new_phone, new_password=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        if new_password: 
            c.execute("UPDATE users SET email=?, phone=?, password_hash=? WHERE username=?", 
                      (new_email, new_phone, hash_password(new_password), old_username))
        else: # Sadece iletişim bilgileri
            c.execute("UPDATE users SET email=?, phone=? WHERE username=?", 
                      (new_email, new_phone, old_username))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def update_amazon_credentials(username, az_email, az_pass):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        sifreli_pass = encrypt_amazon_pass(az_pass)
        c.execute("UPDATE users SET amazon_email=?, amazon_password=? WHERE username=?", 
                  (az_email, sifreli_pass, username))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()        

def update_password_by_email(email, new_password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET password_hash=? WHERE email=?", 
                  (hash_password(new_password), email))
        conn.commit()
        
        return c.rowcount > 0 
    except Exception as e:
        print("Şifre Güncelleme Hatası:", e)
        return False
    finally:
        conn.close()

def delete_user(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return True


# ==========================================
# 5. ANALİZ RAPORLAMA VE KAYIT İŞLEMLERİ
# ==========================================
def save_analysis_result(username, url, risk_score, comment_count):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO analyses (username, target_url, risk_score, analyzed_comments_count) VALUES (?, ?, ?, ?)", 
                  (username, url, risk_score, comment_count))
        conn.commit()
        return True
    except Exception as e:
        print("Analiz Kayıt Hatası:", e)
        return False
    finally:
        conn.close()

def get_user_analyses(username):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT id, target_url, risk_score, analyzed_comments_count, created_at FROM analyses WHERE username=? ORDER BY created_at DESC", (username,))
    
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_analysis_by_id(analysis_id: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,))
    row = c.fetchone()
    conn.close()
    
    return dict(row) if row else None     


# ==========================================
# 6. ÜRÜN TAKİBİ (JOB / TRACKING) İŞLEMLERİ
# ==========================================
def add_tracking(username, target_url, initial_score):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM tracked_items WHERE username=? AND target_url=?", (username, target_url))
        if c.fetchone():
            return False 
            
        c.execute("INSERT INTO tracked_items (username, target_url, last_risk_score) VALUES (?, ?, ?)", 
                  (username, target_url, initial_score))
        conn.commit()
        return True
    except Exception as e:
        print("Takip Ekleme Hatası:", e)
        return False
    finally:
        conn.close()

def get_all_tracked_items():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tracked_items")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_tracked_item_score(item_id, new_score):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("UPDATE tracked_items SET last_risk_score=?, last_checked_at=CURRENT_TIMESTAMP WHERE id=?", 
                  (new_score, item_id))
        conn.commit()
        return True
    except Exception as e:
        print("Takip Güncelleme Hatası:", e)
        return False
    finally:
        conn.close()   

def get_user_tracked_items(username):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tracked_items WHERE username=? ORDER BY created_at DESC", (username,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_tracked_item(item_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tracked_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return True        


# ==========================================
# 7. ADMİN İŞLEMLERİ (YETKİ, YÖNETİM VE LOGLAR)
# ==========================================
def is_user_admin(username):
    """Bir kullanıcının admin olup olmadığını kontrol eder."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def make_admin(username):
    """Bir kullanıcıya admin yetkisi verir."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin=1 WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return True

def get_admin_dashboard_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Toplam Kullanıcı Sayısı
    try:
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
    except Exception as e:
        print(f"[HATA - Users Tablosu]: {e}")
        total_users = 0
    
    # Toplam Yapılan Analiz Sayısı
    try:
        c.execute("SELECT COUNT(*) FROM analyses")
        total_analyses = c.fetchone()[0]
    except Exception as e:
        print(f"[HATA - Analyses Tablosu]: {e}")
        total_analyses = 0
    
    # Aktif Takip Sayısı
    try:
        c.execute("SELECT COUNT(*) FROM tracked_items")
        active_tracking = c.fetchone()[0]
    except Exception as e:
        print(f"[HATA - Tracked Items Tablosu]: {e}")
        active_tracking = 0
    
    # Admin Analiz Trafiği (Grafik için)
    try:
        c.execute("""
            SELECT DATE(created_at) as tarih, COUNT(*) as sayi 
            FROM analyses 
            GROUP BY DATE(created_at) 
            ORDER BY tarih DESC LIMIT 7
        """)
        daily_stats_raw = c.fetchall()
        # Grafiğin soldan sağa doğru akması için veriyi tersine çeviriyoruz
        daily_stats = [{"date": row[0], "count": row[1]} for row in reversed(daily_stats_raw)]
    except Exception as e:
        print(f"[HATA - Grafik Verisi]: {e}")
        daily_stats = []
        
    conn.close()
    
    return {
        "total_users": total_users,
        "total_analyses": total_analyses,
        "active_tracking": active_tracking,
        "daily_stats": daily_stats
    }

def get_all_users(search_term=None):
    """Admin paneli için sistemdeki tüm kullanıcıların listesini getirir. Arama destekler."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        if search_term:
            query = f"%{search_term}%"
            c.execute("""
                SELECT * FROM users 
                WHERE username LIKE ? OR email LIKE ? OR phone LIKE ? 
                ORDER BY id ASC
            """, (query, query, query))
        else:
            c.execute("SELECT * FROM users ORDER BY id ASC")
            
        rows = c.fetchall()
        
        users = []
        for row in rows:
            user_dict = dict(row)
            if 'password' in user_dict:
                del user_dict['password']
            users.append(user_dict)
            
    except Exception as e:
        print(f"[HATA - Kullanıcı Listesi]: {e}")
        users = []
        
    conn.close()
    return users

def update_user_by_admin(user_id: int, email: str, phone: str, is_admin: bool):
    """Admin panelinden kullanıcı bilgilerini ve yetkisini günceller."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        admin_val = 1 if is_admin else 0
        c.execute("""
            UPDATE users 
            SET email = ?, phone = ?, is_admin = ?
            WHERE id = ?
        """, (email, phone, admin_val, user_id))
        
        conn.commit()
        success = c.rowcount > 0
    except Exception as e:
        print(f"[HATA - Admin Güncelleme]: {e}")
        success = False
    finally:
        conn.close()
        
    return success

def delete_user_by_admin(user_id: int):
    """Admin panelinden bir kullanıcıyı sistemden kalıcı olarak siler."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        success = c.rowcount > 0
    except Exception as e:
        print(f"[HATA - Admin Silme]: {e}")
        success = False
    finally:
        conn.close()
        
    return success

def get_global_analysis_history(username_filter=None, date_filter=None):
    """Admin paneli için tüm analiz geçmişini kullanıcı ve tarih filtresiyle getirir."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        query = """
            SELECT id, username, target_url, created_at, risk_score 
            FROM analyses 
            WHERE 1=1
        """
        params = []
        
        if username_filter:
            query += " AND username LIKE ?"
            params.append(f"%{username_filter}%")
            
        if date_filter:
            query += " AND date(created_at) = ?"
            params.append(date_filter)
    
        query += " ORDER BY created_at DESC LIMIT 100"
        
        c.execute(query, params)
        rows = c.fetchall()
        
        history_list = []
        for r in rows:
            history_list.append({
                "id": r["id"],
                "username": r["username"],
                "url": r["target_url"], 
                "created_at": r["created_at"],
                "risk_score": r["risk_score"]
            })
        return history_list
    except Exception as e:
        print(f"[HATA - Log Çekme]: {e}")
        return []
    finally:
        conn.close()

def get_all_tracked_items(username_filter=None):
    """Admin paneli için aktif olarak takip edilen tüm ürünleri çeker (Opsiyonel filtre ile)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        query = """
            SELECT id, username, target_url, last_risk_score, created_at, last_checked_at 
            FROM tracked_items 
            WHERE 1=1
        """
        params = []
        
        if username_filter:
            query += " AND username LIKE ?"
            params.append(f"%{username_filter}%")
            
        query += " ORDER BY created_at DESC"
        
        c.execute(query, params)
        rows = c.fetchall()
        
        tracked_list = []
        for r in rows:
            tracked_list.append({
                "id": r["id"],
                "username": r["username"],
                "url": r["target_url"],
                "risk_score": r["last_risk_score"],
                "created_at": r["created_at"],
                "last_checked_at": r["last_checked_at"]
            })
        return tracked_list
    except Exception as e:
        print(f"[HATA - Takip Edilenleri Çekme]: {e}")
        return []
    finally:
        conn.close()