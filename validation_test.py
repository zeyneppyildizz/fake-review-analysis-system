import pandas as pd
import numpy as np
import joblib
import os
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix, classification_report)

# --- 1. MODELİN OKUYABİLMESİ İÇİN ÖZEL SINIF (ŞART) ---
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

# --- 2. MODELİ YÜKLE ---
# Not: Modeli hangi isimle kaydettiysen onu buraya yaz (Örn: hybrid_meta_stacking.pkl)
model_yolu = 'model_hybrid_meta_stacking_2.pkl'

if not os.path.exists(model_yolu):
    print(f" HATA: {model_yolu} bulunamadı! Lütfen model dosyasının adını kontrol et.")
else:
    model = joblib.load(model_yolu)
    print("model başarıyla yüklendi.")

# --- 3. YENİ OTEL VERİSETİNİ (VALIDATION) YÜKLE VE DÖNÜŞTÜR ---
try:
    # İkinci görseldeki hotel verisinin ismini buraya yaz
    df_val = pd.read_csv('validation_dataset.csv') 
    
    # Sütunları ve Etiketleri Senin Modeline Göre Eşliyoruz
    # text -> text_
    X_val = df_val['text']
    
    # truthful (Gerçek) -> 1 | deceptive (Sahte) -> 0
    y_val = df_val['deceptive'].map({'truthful': 1, 'deceptive': 0})
    
    # Boş satır varsa temizle
    clean_mask = X_val.notna() & y_val.notna()
    X_val = X_val[clean_mask]
    y_val = y_val[clean_mask]

    print(f" Veri seti hazırlandı. Toplam {len(X_val)} yorum test ediliyor...")

    # --- 4. TAHMİN VE ANALİZ ---
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]

    # Metrikleri Hesapla
    acc = accuracy_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred, average='macro')
    auc = roc_auc_score(y_val, y_proba)
    kappa = cohen_kappa_score(y_val, y_pred)
    cm = confusion_matrix(y_val, y_pred)

    # --- 5. SONUÇ RAPORU ---
    print("\n" + "="*95)
    print(" OTEL VERİSETİ (CROSS-DOMAIN) VALIDATION SONUÇLARI")
    print("-" * 95)
    print(f"DOĞRULUK (ACC): {acc:.4f} | F1-SKOR: {f1:.4f} | AUC: {auc:.4f} | KAPPA: {kappa:.4f}")
    print("-" * 95)
    print("KARMAŞIKLIK MATRİSİ:")
    print(f"Doğru Sahte (TN): {cm[0][0]} | Yanlış Gerçek (FP): {cm[0][1]}")
    print(f"Yanlış Sahte (FN): {cm[1][0]} | Doğru Gerçek (TP): {cm[1][1]}")
    print("="*95)

    # Detaylı Analiz
    print("\nSINIFLANDIRMA DETAYLARI:")
    print(classification_report(y_val, y_pred, target_names=['Sahte (Deceptive)', 'Gerçek (Truthful)']))

        # Tahminlerden hemen sonra ekle:
    print("Tahmin edilen sınıfların dağılımı:", pd.Series(y_pred).value_counts())
    print("Gerçek sınıfların dağılımı:", y_val.value_counts())

    # Eğer y_val tamamen NaN ise mapping hatalıdır. Şunu dene:
    print("Mapping öncesi benzersiz değerler:", df_val['deceptive'].unique())

except Exception as e:
    print(f" Bir hata oluştu: {e}")