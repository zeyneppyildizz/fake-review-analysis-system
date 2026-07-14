import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import VotingClassifier 
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             cohen_kappa_score, confusion_matrix)
import joblib

# Veri yükleme
df = pd.read_csv('dataset.csv')
df = df.dropna(subset=['text_'])
y = df['label'].map({'OR': 1, 'CG': 0})

# 1. DÜRÜST YÖNTEM: Önce Bölme
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    df['text_'], y, test_size=0.2, random_state=42, stratify=y
)

# 2. VEKTÖRİZASYON
vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X_train = vectorizer.fit_transform(X_train_raw)
X_test = vectorizer.transform(X_test_raw)

# 3. ENSEMBLE MODEL TANIMI VE EĞİTİMİ
yontem1 = LogisticRegression(max_iter=2000)
yontem2 = LinearSVC(max_iter=2000)
yontem3 = MultinomialNB()

ensemble = VotingClassifier(
    estimators=[('lr', yontem1), ('svc', yontem2), ('nb', yontem3)],
    voting='hard' 
)

print("Ensemble (Karma) Model Eğitiliyor...")
ensemble.fit(X_train, y_train)

# EĞİTİM METRİKLERİ
y_train_pred = ensemble.predict(X_train)
train_acc = accuracy_score(y_train, y_train_pred)
train_f1 = f1_score(y_train, y_train_pred, average='macro')
train_auc = roc_auc_score(y_train, y_train_pred) # Hard voting için tahminler üzerinden
train_kappa = cohen_kappa_score(y_train, y_train_pred)

# TEST METRİKLERİ
y_test_pred = ensemble.predict(X_test)
test_acc = accuracy_score(y_test, y_test_pred)
test_f1 = f1_score(y_test, y_test_pred, average='macro')
test_auc = roc_auc_score(y_test, y_test_pred)
test_kappa = cohen_kappa_score(y_test, y_test_pred)
cm_test = confusion_matrix(y_test, y_test_pred)

# SONUÇLAR
print("-" * 90)
print(f"EĞİTİM -> Doğruluk: {train_acc:.4f} | F1: {train_f1:.4f} | AUC: {train_auc:.4f} | Kappa: {train_kappa:.4f}")
print(f"TEST   -> Doğruluk: {test_acc:.4f}  | F1: {test_f1:.4f}  | AUC: {test_auc:.4f}  | Kappa: {test_kappa:.4f}")
print("-" * 90)
print("KARMAŞIKLIK MATRİSİ (TEST):")
print(f"Doğru Sahte: {cm_test[0][0]} | Yanlış Gerçek: {cm_test[0][1]}")
print(f"Yanlış Sahte: {cm_test[1][0]} | Doğru Gerçek: {cm_test[1][1]}")
print("-" * 90)

# KAYIT
joblib.dump(ensemble, 'model.pkl')
joblib.dump(vectorizer, 'vectorizer.pkl')