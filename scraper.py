import os
import time
import tempfile
import uuid
import shutil
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

def insan_gibi_yaz(element, metin):
    for harf in metin:
        element.send_keys(harf)
        time.sleep(random.uniform(0.05, 0.25))

def get_amazon_reviews_auto(url, email=None, password=None, max_sayfa=10):
    chrome_options = Options()
    
    temp_klasor = None
    ana_profil = None
    
    if email:
        user_name = email.split('@')[0]
        ana_profil = os.path.join(os.getcwd(), "amazon_cookies", f"profil_{user_name}")
        
        benzersiz_id = str(uuid.uuid4().hex)[:6]
        temp_klasor = os.path.join(tempfile.gettempdir(), f"profil_klon_{user_name}_{benzersiz_id}")
        
        if os.path.exists(ana_profil):
            try:
                shutil.copytree(
                    ana_profil, 
                    temp_klasor, 
                    ignore=shutil.ignore_patterns("SingletonLock", "SingletonCookie", "Lock")
                )
            except Exception as e:
                pass
        else:
            os.makedirs(temp_klasor, exist_ok=True)
            
        chrome_options.add_argument(f"--user-data-dir={temp_klasor}")
        print(f"Hafıza devrede (Kilitler temizlendi): {temp_klasor}")
    else:
        temp_klasor = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_klasor}")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("window-size=1200,800")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    reviews = []
    try:
        # ================= AKILLI GİRİŞ =================
        
        print(f" Hedef linke gidiliyor: {url}")
        driver.get(url)
        time.sleep(3)

        if email and password and ("/ap/" in driver.current_url.lower() or "signin" in driver.current_url.lower()):
            print("Oturum kapalı, giriş denemesi yapılıyor...")
            try:
                email_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'email')]")))
                insan_gibi_yaz(email_box, email)
                email_box.send_keys(Keys.ENTER)
                time.sleep(2)
                pass_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'password')]")))
                insan_gibi_yaz(pass_box, password)
                pass_box.send_keys(Keys.ENTER)
                time.sleep(4)
            except: pass

            if "/ap/" in driver.current_url.lower():
                print("🚨 Manuel doğrulama bekleniyor (90 sn)...")
                for i in range(90):
                    if "/ap/" not in driver.current_url.lower(): break
                    time.sleep(1)
        
        # Giriş yapıldıktan sonra Amazon bizi başka yere fırlattıysa tekrar hedefe dön
        if "/ap/" in driver.current_url.lower() or "signin" in driver.current_url.lower():
            print("❌ Giriş başarılamadı, yine de deneniyor...")
        elif driver.current_url != url:
            driver.get(url)
            time.sleep(3)

        # ================= VERİ ÇEKME =================
        
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-hook='review-body']")))

        for sayfa in range(1, max_sayfa):
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            eski_sayi = len(driver.find_elements(By.CSS_SELECTOR, "span[data-hook='review-body']"))
            
            tiklandi_mi = driver.execute_script("""
                var nextBtn = document.querySelector('li.a-last a') || document.querySelector('.a-pagination li:last-child a');
                if (!nextBtn) {
                    var all = document.querySelectorAll('a, button');
                    for (var i = 0; i < all.length; i++) {
                        var txt = (all[i].innerText || "").toLowerCase();
                        if (txt.includes("more reviews") || txt.includes("daha fazla")) { nextBtn = all[i]; break; }
                    }
                }
                if (!nextBtn) return false;
                nextBtn.scrollIntoView(); nextBtn.click(); return true;
            """)

            if not tiklandi_mi: break
            
            try:
                WebDriverWait(driver, 10).until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "span[data-hook='review-body']")) > eski_sayi)
            except: break

        elements = driver.find_elements(By.CSS_SELECTOR, "span[data-hook='review-body']")
        for el in elements:
            text = el.text.strip()
            if text and text not in reviews: reviews.append(text)
            
        print(f"✅ Toplam {len(reviews)} yorum çekildi.")
        return reviews

    except Exception as e:
        print(f"🛑 Hata: {e}")
        return reviews
    finally:
        driver.quit()
        
        if email and temp_klasor and os.path.exists(temp_klasor):
            try:
                if ana_profil:
                    if os.path.exists(ana_profil):
                        shutil.rmtree(ana_profil, ignore_errors=True)
                    shutil.copytree(
                        temp_klasor, 
                        ana_profil,
                        ignore=shutil.ignore_patterns("SingletonLock", "SingletonCookie", "Lock")
                    )
                
                shutil.rmtree(temp_klasor, ignore_errors=True)
            except Exception as e:
                print(f"Profil senkronizasyon hatası: {e}")