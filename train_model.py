import pandas as pd
from xgboost import XGBClassifier
import joblib
import os

# =============================
# TREINA MODELO COMPATÍVEL COM XGBoost 2.0.3
# =============================
print("Lendo dados...")
df = pd.read_csv("data/brasileirao.csv")

features = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
X = df[features]
y = df['home_win']  # 1 = vitória do mandante

print(f"Treinando com {len(df)} jogos...")
model = XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    eval_metric='logloss'
)
model.fit(X, y)

# SALVA COM FORMATO COMPATÍVEL
model_path = "model.pkl"
joblib.dump(model, model_path)
print(f"Modelo salvo em: {os.path.abspath(model_path)}")
print(f"Classes: {model.classes_}")
print(f"Features: {model.feature_names_in_}")
