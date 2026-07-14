import pandas as pd
import os
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix)
import joblib

# Veri Hazırlığı
df = pd.read_csv('dataset.csv').dropna(subset=['text_'])
y = df['label'].map({'OR': 1, 'CG': 0})
X_train, X_test, y_train, y_test = train_test_split(df['text_'], y, test_size=0.2, random_state=42, stratify=y)

# Pipeline Tanımı
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(sublinear_tf=True, strip_accents='unicode')),
    ('clf', LinearSVC(class_weight='balanced', max_iter=5000, random_state=42))
])

# İnce Ayar (Fine-Tuning) Parametreleri
param_grid = {
    'tfidf__max_features': [20000, 25000, 30000],
    'tfidf__ngram_range': [(1, 3)],
    'tfidf__min_df': [3, 4],
    'clf__C': [0.3, 0.4, 0.5, 0.6, 0.7]
}

print("İnce ayar başlatıldı (Tüm metrikler hazırlanıyor)...")
grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='accuracy', n_jobs=-1, verbose=1)
grid_search.fit(X_train, y_train)

# En İyi Modeli Seç
best_model = grid_search.best_estimator_

# ==========================================
# 1. EĞİTİM (TRAIN) METRİKLERİ
# ==========================================
y_train_pred = best_model.predict(X_train)
train_acc = accuracy_score(y_train, y_train_pred)
train_f1 = f1_score(y_train, y_train_pred, average='macro')
train_auc = roc_auc_score(y_train, best_model.decision_function(X_train))
train_kappa = cohen_kappa_score(y_train, y_train_pred)

# ==========================================
# 2. TEST METRİKLERİ
# ==========================================
y_test_pred = best_model.predict(X_test)
test_acc = accuracy_score(y_test, y_test_pred)
test_f1 = f1_score(y_test, y_test_pred, average='macro')
test_auc = roc_auc_score(y_test, best_model.decision_function(X_test))
test_kappa = cohen_kappa_score(y_test, y_test_pred)
cm_test = confusion_matrix(y_test, y_test_pred)

# ==========================================
# 📊 TÜM SONUÇLAR (SS FORMATINDA)
# ==========================================
print("\n" + "="*90)
print(f"EN İYİ PARAMETRELER: {grid_search.best_params_}")
print("-" * 90)
print(f"EĞİTİM -> Doğruluk: {train_acc:.4f} | F1: {train_f1:.4f} | AUC: {train_auc:.4f} | Kappa: {train_kappa:.4f}")
print(f"TEST   -> Doğruluk: {test_acc:.4f} | F1: {test_f1:.4f} | AUC: {test_auc:.4f} | Kappa: {test_kappa:.4f}")
print("-" * 90)
print("KARMAŞIKLIK MATRİSİ (TEST):")
print(f"Doğru Sahte: {cm_test[0][0]} | Yanlış Gerçek: {cm_test[0][1]}")
print(f"Yanlış Sahte: {cm_test[1][0]} | Doğru Gerçek: {cm_test[1][1]}")
print("="*90 + "\n")

# ==========================================
# KAYIT (Senin Klasörün)
# ==========================================

joblib.dump(best_model, 'model_fine_tuning_final.pkl')
