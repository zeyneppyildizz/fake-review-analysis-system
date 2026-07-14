import pandas as pd
import numpy as np
import joblib
import os
import time
from sklearn.base import BaseEstimator, TransformerMixin
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
def get_amazon_reviews_selenium(url, sayfa_sayisi=71): 
    print(f"\n🌐 Sınırsız Tarama Modu Başlatılıyor... (Maksimum {sayfa_sayisi} sayfa)")
    
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(url)
        print("\n" + "="*60)
        print("TARAYICI BEKLEMEDE")
        print("Lütfen yorumları görene kadar bekleyin (giriş/captcha gerekirse yapın).")
        print("Yorumlar hazır olduğunda buraya gelip ENTER'a basın.")
        print("="*60)
        
        input("\n> Analizi Başlatmak İçin ENTER... ")
        
        reviews = []
        sayfa_sayacı = 1
        
        while sayfa_sayacı <= sayfa_sayisi:
            time.sleep(2)
            
            # 1. Mevcut sayfadaki yorumları topla
            review_elements = driver.find_elements(By.CSS_SELECTOR, "span[data-hook='review-body']")
            yeni_eklenen = 0
            for element in review_elements:
                text = element.text.strip()
                if text and text not in reviews:
                    reviews.append(text)
                    yeni_eklenen += 1
            
            print(f"Sayfa {sayfa_sayacı} tarandı. (+{yeni_eklenen} yorum. Toplam: {len(reviews)})")
            
            # 2. İlerlemek için buton ara
            found_button = False
            
            # Önce klasik 'Next' butonuna bak
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.a-last a")
                driver.execute_script("arguments[0].click();", next_button)
                found_button = True
            except:
                # 'Next' yoksa 'Show More' butonuna bak
                try:
                    show_more_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'more reviews')]"
                    show_more_btn = driver.find_element(By.XPATH, show_more_xpath)
                    driver.execute_script("arguments[0].click();", show_more_btn)
                    found_button = True
                except:
                    found_button = False

            # Eğer hiçbir buton bulunamadıysa yolun sonuna geldik demektir
            if not found_button:
                print("🏁 Tüm yorumlar toplandı veya başka sayfa kalmadı.")
                break
            
            sayfa_sayacı += 1
            time.sleep(3) 
            
        return reviews
        
    except Exception as e:
        print(f"Selenium bir hatayla karşılaştı: {e}")
        return []
        
    finally:
        driver.quit()

# --- 3. MODEL İLE ANALİZ FONKSİYONU ---
def analyze_reviews(reviews):
    model_yolu = 'modellerim/model_stcking_ensemble_with_TF_IDF_VAL.pkl'
    
    if not os.path.exists(model_yolu):
        print(f"Model dosyası bulunamadı: {model_yolu}")
        return
        
    print("🧠 Şampiyon Model yorumları analiz ediyor...\n")
    model = joblib.load(model_yolu)
    
    df_reviews = pd.DataFrame({'text_': reviews})
    predictions = model.predict(df_reviews['text_'])
    probabilities = model.predict_proba(df_reviews['text_'])
    
    print("="*80)
    print("CANLI YORUM ANALİZ RAPORU ")
    print("="*80)
    
    sahte_sayisi = 0
    gercek_sayisi = 0
    
    for i, (text, pred, prob) in enumerate(zip(reviews, predictions, probabilities)):
        durum = "GERÇEK (OR)" if pred == 1 else "SAHTE (CG)"
        guven_orani = prob[1] if pred == 1 else prob[0]
        
        if pred == 1: gercek_sayisi += 1
        else: sahte_sayisi += 1
        
        kisa_metin = text.replace('\n', ' ')[:100] + "..." if len(text) > 100 else text.replace('\n', ' ')
        
        ikon = "" if pred == 1 else ""
        print(f"{ikon} Yorum {i+1} | Karar: {durum} (Güven: %{guven_orani*100:.1f})")
        print(f"   Metin: {kisa_metin}\n")
        
    print("="*80)
    print(f"📊 ÖZET: Toplam {len(reviews)} yorum incelendi.")
    print(f"   Gerçek Yorumlar: {gercek_sayisi}")
    print(f"   Sahte Yorumlar:  {sahte_sayisi}")
    print("="*80)

# --- ANA PROGRAM ÇALIŞTIRMA ---
if __name__ == "__main__":
    ornek_link = input("Analiz edilecek Amazon Yorum Linkini yapıştırın:\n> ")
    
    if ornek_link:
        cekilen_yorumlar = get_amazon_reviews_selenium(ornek_link, sayfa_sayisi=71)
        if cekilen_yorumlar:
            analyze_reviews(cekilen_yorumlar)
        else:
            print("Yorum bulunamadı veya bir hata oluştu.")