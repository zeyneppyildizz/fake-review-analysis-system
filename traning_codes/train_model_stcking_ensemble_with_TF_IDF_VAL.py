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
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix)

# --- ÖZEL ÖZELLİK ÇIKARICI ---
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

# --- VERİ HAZIRLIĞI VE YOLLU BÖLME ---
print("Veri yükleniyor ve 3 parçaya bölünüyor...")
df = pd.read_csv('dataset.csv').dropna(subset=['text_'])
y = df['label'].map({'OR': 1, 'CG': 0})

X_temp, X_val, y_temp, y_val = train_test_split(df['text_'], y, test_size=0.20, random_state=42, stratify=y)
X_train, X_test, y_train, y_test = train_test_split(X_temp, y_temp, test_size=0.20, random_state=42, stratify=y_temp)

print(f"Eğitim Seti: {len(X_train)} | Test Seti: {len(X_test)} | Doğrulama Seti: {len(X_val)}")

# --- HİBRİT PIPELINE YAPISI ---
features = FeatureUnion([
    ('tfidf', TfidfVectorizer(sublinear_tf=True, max_features=30000, ngram_range=(1, 3), min_df=3)),
    ('stats', Pipeline([
        ('extract', TextStatsTransformer()),
        ('scaler', StandardScaler())
    ]))
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

# --- EĞİTİM ---
print("\nStacking Ensemble eğitiliyor.")
full_pipeline.fit(X_train, y_train)

# --- 5. RAPORLAMA FONKSİYONU ---
def print_full_report(name, X, y_true):
    y_pred = full_pipeline.predict(X)
    y_proba = full_pipeline.predict_proba(X)[:, 1]
    
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average='macro')
    auc = roc_auc_score(y_true, y_proba)
    kappa = cohen_kappa_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    
    print(f"\n {name} SONUÇLARI")
    print("-" * 60)
    print(f"Doğruluk: {acc:.4f} | F1: {f1:.4f} | AUC: {auc:.4f} | Kappa: {kappa:.4f}")
    print(f"Karmaşıklık Matrisi: TN: {cm[0][0]} | FP: {cm[0][1]} | FN: {cm[1][0]} | TP: {cm[1][1]}")

# Sonuçları Bas
print_full_report("EĞİTİM (TRAIN)", X_train, y_train)
print_full_report("ARA TEST (TEST)", X_test, y_test)
print_full_report("FİNAL DOĞRULAMA (VALIDATION)", X_val, y_val)

# --- 6. KAYIT ---
os.makedirs("modellerim", exist_ok=True)
joblib.dump(full_pipeline, 'modellerim/model_stcking_ensemble_with_TF_IDF_VAL.pkl')
print("\n Şampiyon model 'modellerim/final_triple_split_model.pkl' olarak kaydedildi.")