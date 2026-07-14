import pandas as pd
import numpy as np
import joblib
import os
import time
from sklearn.base import BaseEstimator, TransformerMixin

# Selenium Kütüphaneleri
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. MODELİN İHTİYACI OLAN ÖZEL SINIF (ZORUNLU) ---
class TextStatsTransformer(BaseEstimator, TransformerMixin):
    def fit(self, x, y=None): return self
    def transform(self, posts):
        return np.array([
            [len(text), 
             len(text.split()), 
             text.count('!'), 
             text.count('?'), 
             sum(1 for c in text if c.isupper()) / (len(text) + 1)
            ] for text in posts
        ])

# --- 2. SELENIUM İLE YORUM ÇEKME FONKSİYONU ---
def get_amazon_reviews_selenium(url):
    print("\nChrome tarayıcısı başlatılıyor...")
    
    # Tarayıcı ayarları (Arka planda değil, GÖRÜNÜR şekilde açılacak)
    chrome_options = Options()
    # Amazon bot olduğumuzu anlamasın diye birkaç güvenlik ayarı kapatılıyor
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Chrome'u otomatik indirip başlat
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(url)
        print("\n" + "="*60)
        print("🛑 DİKKAT: Tarayıcı açıldı!")
        print("Eğer Amazon 'Giriş Yap' veya 'Robot Musun?' ekranı çıkardıysa:")
        print("1. Açılan tarayıcıda manuel olarak giriş yap veya Captcha'yı çöz.")
        print("2. Yorumları ekranda net bir şekilde görene kadar bekle.")
        print("3. Yorumları gördükten sonra BURAYA (Konsola) tıklayıp ENTER'a bas.")
        print("="*60)
        
        input("\n> Devam etmek için ENTER tuşuna basın... ")
        
        print("\n🔍 Yorumlar toplanıyor, lütfen bekleyin...")
        # Sayfanın tam yüklenmesi için ufak bir bekleme süresi
        time.sleep(3) 
        
        reviews = []
        # Amazon yorum metinlerinin bulunduğu HTML etiketlerini buluyoruz
        review_elements = driver.find_elements(By.CSS_SELECTOR, "span[data-hook='review-body']")
        
        for element in review_elements:
            text = element.text.strip()
            if text:
                reviews.append(text)
                
        print(f"✅ Başarılı! Sayfadan {len(reviews)} adet yorum çekildi.\n")
        return reviews
        
    except Exception as e:
        print(f"❌ Selenium bir hatayla karşılaştı: {e}")
        return []
        
    finally:
        # İşlem bitince tarayıcıyı kapat
        print("🧹 Tarayıcı kapatılıyor...")
        driver.quit()

# --- 3. MODEL İLE ANALİZ FONKSİYONU ---
def analyze_reviews(reviews):
    model_yolu = 'modellerim/model_stcking_ensemble_with_TF_IDF_VAL.pkl'
    
    if not os.path.exists(model_yolu):
        print(f"❌ Model dosyası bulunamadı: {model_yolu}")
        return
        
    print("🧠 Şampiyon Model yorumları analiz ediyor...\n")
    model = joblib.load(model_yolu)
    
    df_reviews = pd.DataFrame({'text_': reviews})
    predictions = model.predict(df_reviews['text_'])
    probabilities = model.predict_proba(df_reviews['text_'])
    
    print("="*80)
    print(" 🕵️‍♂️ CANLI YORUM ANALİZ RAPORU ")
    print("="*80)
    
    sahte_sayisi = 0
    gercek_sayisi = 0
    
    for i, (text, pred, prob) in enumerate(zip(reviews, predictions, probabilities)):
        durum = "GERÇEK (OR)" if pred == 1 else "SAHTE (CG)"
        guven_orani = prob[1] if pred == 1 else prob[0]
        
        if pred == 1: gercek_sayisi += 1
        else: sahte_sayisi += 1
        
        kisa_metin = text.replace('\n', ' ')[:100] + "..." if len(text) > 100 else text.replace('\n', ' ')
        
        ikon = "✅" if pred == 1 else "🚨"
        print(f"{ikon} Yorum {i+1} | Karar: {durum} (Güven: %{guven_orani*100:.1f})")
        print(f"   Metin: {kisa_metin}\n")
        
    print("="*80)
    print(f"📊 ÖZET: Toplam {len(reviews)} yorum incelendi.")
    print(f"   Gerçek Yorumlar: {gercek_sayisi}")
    print(f"   Sahte Yorumlar:  {sahte_sayisi}")
    print("="*80)

# --- ANA PROGRAM ÇALIŞTIRMA ---
if __name__ == "__main__":
    ornek_link = input("🔍 Analiz edilecek Amazon Yorum Linkini yapıştırın:\n> ")
    
    if ornek_link:
        cekilen_yorumlar = get_amazon_reviews_selenium(ornek_link)
        if cekilen_yorumlar:
            analyze_reviews(cekilen_yorumlar)
        else:
            print("Yorum bulunamadı. Lütfen sayfada yorumların olduğundan emin olun.")