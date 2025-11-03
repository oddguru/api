import pandas as pd
from xgboost import XGBClassifier
import joblib

# Carrega dados
df = pd.read_csv('data/brasileirao.csv')

# Features (exemplo realista)
features = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
X = df[features]
y = df['home_win']  # 1 = vitória do mandante

# Treina
model = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
model.fit(X, y)

# Salva
joblib.dump(model, 'model.pkl')
print("Modelo treinado e salvo como model.pkl")
