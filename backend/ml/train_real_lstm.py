"""
Real Soil Moisture & Microclimate IoT Forecaster (LSTM)
Fetches genuine daily multi-year reanalysis data (2020-2024) across 5 agro-climatic zones in Tamil Nadu
(Thanjavur, Madurai, Coimbatore, Tiruchirappalli, Salem) via Open-Meteo.
Trains a 2-layer LSTM on RTX 4050 to predict multi-horizon future soil moisture (1, 3, 7, 14 days)
from IoT inputs: [Soil Moisture, Temperature, Relative Humidity, Rainfall, Wind Speed].
"""

import os
import json
import time
import urllib.request
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Coordinates for major TN agricultural zones
TN_LOCATIONS = [
    {"name": "Thanjavur (Cauvery Delta)", "lat": 10.7870, "lon": 79.1378},
    {"name": "Madurai (Southern)", "lat": 9.9252, "lon": 78.1198},
    {"name": "Coimbatore (Western)", "lat": 11.0168, "lon": 76.9558},
    {"name": "Tiruchirappalli (Central)", "lat": 10.7905, "lon": 78.7047},
    {"name": "Salem (North-Western)", "lat": 11.6643, "lon": 78.1460},
]

SEQUENCE_LENGTH = 30  # 30-day IoT historical lookback
HORIZONS = [1, 3, 7, 14]  # Days ahead forecast

class SoilLSTM(nn.Module):
    def __init__(self, input_dim=5, hidden_dim=64, num_layers=2, output_dim=4):
        super(SoilLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers=num_layers,
            batch_first=True, dropout=0.2
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim)
        )

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # Last time step
        return self.fc(out)

def fetch_real_tn_timeseries():
    all_records = []
    print("Fetching real historical weather & soil moisture from Open-Meteo for TN regions...")
    for loc in TN_LOCATIONS:
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={loc['lat']}&longitude={loc['lon']}&"
            f"start_date=2021-01-01&end_date=2024-01-01&"
            f"daily=soil_moisture_0_to_7cm_mean,temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,wind_speed_10m_max&"
            f"timezone=auto"
        )
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                d = data['daily']
                # features: [soil_moisture, temp, humidity, precip, wind]
                sm = np.array(d['soil_moisture_0_to_7cm_mean'], dtype=np.float32)
                temp = np.array(d['temperature_2m_mean'], dtype=np.float32)
                rh = np.array(d['relative_humidity_2m_mean'], dtype=np.float32)
                precip = np.array(d['precipitation_sum'], dtype=np.float32)
                wind = np.array(d['wind_speed_10m_max'], dtype=np.float32)
                
                # Replace None or NaNs with forward fill
                arr = np.column_stack([sm, temp, rh, precip, wind])
                arr = np.nan_to_num(arr, nan=0.2)
                all_records.append(arr)
                print(f"  Loaded {len(arr)} daily time-steps for {loc['name']}")
                time.sleep(0.5)
        except Exception as e:
            print(f"  Error fetching {loc['name']}: {e}")
    return all_records

def create_sequences(datasets, seq_len=30, horizons=[1, 3, 7, 14]):
    X, y = [], []
    max_h = max(horizons)
    for ds in datasets:
        for i in range(len(ds) - seq_len - max_h):
            seq = ds[i : i + seq_len]
            targets = [ds[i + seq_len + h - 1, 0] for h in horizons]
            X.append(seq)
            y.append(targets)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

def train_lstm():
    print("=" * 60)
    print(f"4. Training Soil Moisture / IoT Forecaster on {DEVICE}")
    print("=" * 60)
    
    datasets = fetch_real_tn_timeseries()
    if not datasets:
        print("Failed to fetch real time-series.")
        return
        
    X, y = create_sequences(datasets, SEQUENCE_LENGTH, HORIZONS)
    print(f"Generated {len(X)} sequential windows of length {SEQUENCE_LENGTH}.")
    
    # Train-test split preserving temporal chunks
    split_idx = int(len(X) * 0.85)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Normalize features
    scaler = StandardScaler()
    N_tr, L, F = X_train.shape
    X_train_flat = scaler.fit_transform(X_train.reshape(-1, F))
    X_train = X_train_flat.reshape(N_tr, L, F)
    
    N_te = X_test.shape[0]
    X_test_flat = scaler.transform(X_test.reshape(-1, F))
    X_test = X_test_flat.reshape(N_te, L, F)
    
    train_loader = DataLoader(
        list(zip(torch.tensor(X_train), torch.tensor(y_train))),
        batch_size=32, shuffle=True
    )
    
    model = SoilLSTM(input_dim=F, hidden_dim=64, num_layers=2, output_dim=len(HORIZONS)).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    criterion = nn.HuberLoss()
    
    print("Training LSTM epochs...")
    model.train()
    for epoch in range(1, 26):
        total_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:02d}/25 - Loss: {total_loss/len(train_loader):.4f}")
            
    # Test evaluation
    model.eval()
    with torch.no_grad():
        test_preds = model(torch.tensor(X_test).to(DEVICE)).cpu().numpy()
        test_mae = np.mean(np.abs(test_preds - y_test))
        test_r2 = 1 - (np.sum((test_preds - y_test)**2) / np.sum((y_test - np.mean(y_test))**2))
        print(f"\n--- LSTM Real Data Performance ---")
        print(f"Test MAE: {test_mae:.4f} m³/m³ soil moisture")
        print(f"Test R²: {test_r2:.4f}")
        for idx, h in enumerate(HORIZONS):
            h_mae = np.mean(np.abs(test_preds[:, idx] - y_test[:, idx]))
            print(f"  Horizon +{h} day MAE: {h_mae:.4f}")
            
    # Save model and scaler
    model_path = os.path.join(CHECKPOINTS_DIR, "lstm_soil_forecaster_real.pt")
    scaler_path = os.path.join(CHECKPOINTS_DIR, "lstm_soil_scaler.joblib")
    torch.save(model.state_dict(), model_path)
    joblib.dump(scaler, scaler_path)
    print(f"Saved real LSTM checkpoint to {model_path}")

if __name__ == "__main__":
    train_lstm()
