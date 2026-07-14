import pandas as pd
import numpy as np
import joblib
import os
from sklearn.base import BaseEstimator, TransformerMixin

class TextStatsTransformer(BaseEstimator, TransformerMixin):
    def fit(self, x, y=None): return self
    def transform(self, posts):
        return np.array([[len(t), len(t.split()), t.count('!'), t.count('?'), 
                          sum(1 for c in t if c.isupper())/(len(t)+1)] for t in posts])

import __main__
__main__.TextStatsTransformer = TextStatsTransformer

MODEL_PATH = 'modellerim/model_stcking_ensemble_with_TF_IDF_VAL.pkl'

def perform_analysis(cekilen_yorumlar):
    if not os.path.exists(MODEL_PATH):
        return None
        
    model = joblib.load(MODEL_PATH)
    predictions = model.predict(cekilen_yorumlar)
    probabilities = model.predict_proba(cekilen_yorumlar)
    
    detaylar = []
    g_sayisi, s_sayisi = 0, 0
    
    for text, pred, prob in zip(cekilen_yorumlar, predictions, probabilities):
        durum = "GERÇEK" if pred == 1 else "SAHTE"
        guven = float(prob[1] if pred == 1 else prob[0])
        
        if pred == 1: g_sayisi += 1
        else: s_sayisi += 1
            
        detaylar.append({
            "metin": text, "karar": durum, "guven_skoru": round(guven * 100, 1)
        })
    
    return {
        "ozet": {
            "toplam_yorum": len(cekilen_yorumlar),
            "gercek_yorum_sayisi": g_sayisi,
            "sahte_yorum_sayisi": s_sayisi,
            "sahtelik_orani": round((s_sayisi / len(cekilen_yorumlar)) * 100, 1)
        },
        "yorumlar": detaylar
    }