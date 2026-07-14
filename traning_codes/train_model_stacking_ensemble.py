import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix)
import joblib

# 1. Veri Hazırlığı
df = pd.read_csv('dataset.csv').dropna(subset=['text_'])
y = df['label'].map({'OR': 1, 'CG': 0})
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    df['text_'], y, test_size=0.2, random_state=42, stratify=y
)

# 2. Vektörizör (En iyi parametrelerin)
vectorizer = TfidfVectorizer(
    sublinear_tf=True, 
    max_features=30000,
    ngram_range=(1, 3),
    min_df=3
)

# 3. YENİ GÜÇLÜ TAKIM (Base Estimators)
# NB yerine RandomForest ekleyerek 'karar ağacı' mantığını dahil ediyoruz
base_models = [
    ('svc', LinearSVC(C=0.5, class_weight='balanced', max_iter=5000, random_state=42)),
    ('rf', RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42, n_jobs=-1)),
    ('lr', LogisticRegression(max_iter=2000, C=0.5, random_state=42))
]

# 4. Meta Model
meta_model = LogisticRegression()

# 5. Stacking Yapısı
stacking_model = StackingClassifier(
    estimators=base_models,
    final_estimator=meta_model,
    cv=5, 
    n_jobs=-1
)

model = Pipeline([
    ('tfidf', vectorizer),
    ('stacking', stacking_model)
])

print("Yeni Hibrit Stacking (SVC + RF + LR) eğitiliyor...")
model.fit(X_train_raw, y_train)

# ==========================================
# 📊 RAPORLAMA (TÜM METRİKLER)
# ==========================================

y_train_pred = model.predict(X_train_raw)
y_test_pred = model.predict(X_test_raw)
y_test_proba = model.predict_proba(X_test_raw)[:, 1]

cm_test = confusion_matrix(y_test, y_test_pred)

print("\n" + "="*90)
print("GÜÇLENDİRİLMİŞ STACKING SONUÇLARI")
print("-" * 90)
print(f"EĞİTİM -> Doğruluk: {accuracy_score(y_train, y_train_pred):.4f} | F1: {f1_score(y_train, y_train_pred):.4f}")
print(f"TEST   -> Doğruluk: {accuracy_score(y_test, y_test_pred):.4f} | F1: {f1_score(y_test, y_test_pred):.4f} | AUC: {roc_auc_score(y_test, y_test_proba):.4f}")
print("-" * 90)
print("KARMAŞIKLIK MATRİSİ (TEST):")
print(f"Doğru Sahte: {cm_test[0][0]} | Yanlış Gerçek: {cm_test[0][1]}")
print(f"Yanlış Sahte: {cm_test[1][0]} | Doğru Gerçek: {cm_test[1][1]}")
print("="*90 + "\n")

# 6. Kayıt

joblib.dump(model, 'model_hybrid_stacking_final.pkl')