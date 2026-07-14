import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix)
import joblib

# Veri yükleme
df = pd.read_csv('dataset.csv')
df = df.dropna(subset=['text_'])
y = df['label'].map({'OR': 1, 'CG': 0})

# 1. DÜRÜST YÖNTEM: Önce Bölme (Pipeline içinde vektörizasyon yapılacağı için ham metinler kalır)
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    df['text_'], y, test_size=0.2, random_state=42, stratify=y
)

# 2. PIPELINE TANIMI
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(sublinear_tf=True)),
    ('clf', LinearSVC(class_weight='balanced', max_iter=3000))
])

# 3. GRID SEARCH PARAMETRELERİ
param_grid = {
    'tfidf__max_features': [10000, 15000, 20000],  
    'tfidf__ngram_range': [(1, 2), (1, 3)],        
    'tfidf__min_df': [2, 3],                      
    'clf__C': [0.1, 0.5, 1.0]                      
}

print("GridSearchCV Başlatıldı (Bu işlem zaman alabilir)...")
grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='accuracy', n_jobs=-1, verbose=1)
grid_search.fit(X_train_raw, y_train)

# EN İYİ MODELİN SEÇİLMESİ
best_model = grid_search.best_estimator_

# EĞİTİM METRİKLERİ (En İyi Model ile)
y_train_pred = best_model.predict(X_train_raw)
train_acc = accuracy_score(y_train, y_train_pred)
train_f1 = f1_score(y_train, y_train_pred, average='macro')
train_auc = roc_auc_score(y_train, best_model.decision_function(X_train_raw))
train_kappa = cohen_kappa_score(y_train, y_train_pred)

# TEST METRİKLERİ
y_test_pred = best_model.predict(X_test_raw)
test_acc = accuracy_score(y_test, y_test_pred)
test_f1 = f1_score(y_test, y_test_pred, average='macro')
test_auc = roc_auc_score(y_test, best_model.decision_function(X_test_raw))
test_kappa = cohen_kappa_score(y_test, y_test_pred)
cm_test = confusion_matrix(y_test, y_test_pred)

# SONUÇLAR
print("\n" + "="*90)
print(f"EN İYİ PARAMETRELER: {grid_search.best_params_}")
print("-" * 90)
print(f"EĞİTİM -> Doğruluk: {train_acc:.4f} | F1: {train_f1:.4f} | AUC: {train_auc:.4f} | Kappa: {train_kappa:.4f}")
print(f"TEST   -> Doğruluk: {test_acc:.4f}  | F1: {test_f1:.4f}  | AUC: {test_auc:.4f}  | Kappa: {test_kappa:.4f}")
print("-" * 90)
print("KARMAŞIKLIK MATRİSİ (TEST):")
print(f"Doğru Sahte: {cm_test[0][0]} | Yanlış Gerçek: {cm_test[0][1]}")
print(f"Yanlış Sahte: {cm_test[1][0]} | Doğru Gerçek: {cm_test[1][1]}")
print("="*90 + "\n")

# KAYIT
joblib.dump(best_model, 'best_grid_model.pkl')
print("En iyi model kaydedildi.")