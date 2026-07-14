import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix)

# --- 1. ÖZEL ÖZELLİK ÇIKARICI ---
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

# --- 2. VERİ HAZIRLIĞI ---
df = pd.read_csv('dataset.csv').dropna(subset=['text_'])
y = df['label'].map({'OR': 1, 'CG': 0})
X_train, X_test, y_train, y_test = train_test_split(df['text_'], y, test_size=0.2, random_state=42, stratify=y)

# --- 3. PIPELINE YAPISI ---
features = FeatureUnion([
    ('tfidf', TfidfVectorizer(sublinear_tf=True, max_features=30000, ngram_range=(1, 3), min_df=3)),
    ('stats', TextStatsTransformer())
])

base_models = [
    ('svc', LinearSVC(C=0.4, class_weight='balanced', max_iter=5000, random_state=42)),
    ('rf', RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)),
    ('lr', LogisticRegression(max_iter=2000, C=0.4, random_state=42))
]

full_pipeline = Pipeline([
    ('features', features),
    ('stacking', StackingClassifier(estimators=base_models, final_estimator=LogisticRegression(), cv=5, n_jobs=-1))
])

print("Hibrit Model eğitiliyor, tüm metrikler hesaplanıyor...")
full_pipeline.fit(X_train, y_train)

# --- 4. METRİK HESAPLAMA (Burayı kontrol et, fonksiyonun aynı kalsın) ---
def get_metrics(model, X, y_true):
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]
    
    return {
        'acc': accuracy_score(y_true, y_pred),
        'f1': f1_score(y_true, y_pred, average='macro'),
        'auc': roc_auc_score(y_true, y_proba),
        'kappa': cohen_kappa_score(y_true, y_pred),
        'cm': confusion_matrix(y_true, y_pred)
    }

train_m = get_metrics(full_pipeline, X_train, y_train)
test_m = get_metrics(full_pipeline, X_test, y_test)

# --- 5. EKSİKSİZ SONUÇ TABLOSU (HATA BURADAYDI, DÜZELTİLDİ) ---
print("\n" + "="*95)
print(f"EĞİTİM -> Doğruluk: {train_m['acc']:.4f} | F1: {train_m['f1']:.4f} | AUC: {train_m['auc']:.4f} | Kappa: {train_m['kappa']:.4f}")
print(f"TEST   -> Doğruluk: {test_m['acc']:.4f} | F1: {test_m['f1']:.4f} | AUC: {test_m['auc']:.4f} | Kappa: {test_m['kappa']:.4f}")
print("-" * 95)
print("KARMAŞIKLIK MATRİSİ (TEST):")
print(f"Doğru Sahte: {test_m['cm'][0][0]} | Yanlış Gerçek: {test_m['cm'][0][1]}")
print(f"Yanlış Sahte: {test_m['cm'][1][0]} | Doğru Gerçek: {test_m['cm'][1][1]}")
print("="*95 + "\n")

# Kayıt
joblib.dump(full_pipeline, 'model_hybrid_meta_stacking.pkl')