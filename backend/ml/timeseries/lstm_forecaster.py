"""
LSTM Soil Moisture & Water Stress Forecaster

PyTorch LSTM model predicting future soil moisture levels across
multiple forecast horizons (1, 3, 7, 14 days).

Architecture:
    Input sequence (L, F) →
    LSTM(hidden=64, layers=2, dropout=0.2) →
    Linear(64, H) →
    Output (H,) for each horizon

Training uses synthetic time-series data generated from correlated
weather patterns. Time-aware train/test split prevents data leakage.
"""

import json
import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from ml import DEVICE, CHECKPOINTS_DIR, REPORTS_DIR


# ── Configuration ─────────────────────────────────────────────
SEQUENCE_LENGTH = 30  # Days of historical input
FORECAST_HORIZONS = [1, 3, 7, 14]  # Days ahead
N_INPUT_FEATURES = 6  # temp, humidity, rainfall, wind, solar, soil_moisture

FEATURE_NAMES = [
    "temperature_c", "humidity_pct", "rainfall_mm",
    "wind_speed_kmh", "solar_radiation", "soil_moisture_pct",
]


class SoilMoistureDataset(Dataset):
    """
    Time-series dataset for soil moisture forecasting.
    Each sample is a (sequence, targets) pair where:
        sequence: (SEQUENCE_LENGTH, N_INPUT_FEATURES) historical window
        targets: (len(FORECAST_HORIZONS),) future soil moisture values
    """

    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMForecaster(nn.Module):
    """
    Multi-horizon LSTM forecaster for soil moisture.
    """

    def __init__(
        self,
        input_size: int = N_INPUT_FEATURES,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        n_horizons: int = len(FORECAST_HORIZONS),
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        self.head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, n_horizons),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, L, F) input sequence
        Returns:
            (B, H) predictions for each forecast horizon
        """
        # LSTM output: (B, L, hidden_size)
        lstm_out, _ = self.lstm(x)
        # Use the last time step
        last_hidden = lstm_out[:, -1, :]  # (B, hidden_size)
        return self.head(last_hidden)


def generate_synthetic_timeseries(
    n_days: int = 1000,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate synthetic daily weather + soil moisture time series.
    
    Soil moisture depends on rainfall, temperature, and has
    autoregressive behavior (yesterday's moisture affects today's).
    
    Returns:
        Array of shape (n_days, N_INPUT_FEATURES)
    """
    rng = np.random.RandomState(seed)
    
    # Generate base weather patterns with seasonality
    days = np.arange(n_days)
    season = np.sin(2 * np.pi * days / 365)  # Annual cycle
    
    # Temperature: seasonal + noise
    temp = 27 + 6 * season + rng.normal(0, 2, n_days)
    
    # Humidity: inversely correlated with temp + noise
    humidity = 70 - 10 * season + rng.normal(0, 8, n_days)
    humidity = np.clip(humidity, 20, 100)
    
    # Rainfall: seasonal (monsoon pattern) + noise
    rainfall_base = np.maximum(0, 5 + 8 * np.sin(2 * np.pi * (days - 90) / 365))
    rainfall = np.maximum(0, rainfall_base + rng.exponential(3, n_days) * (rainfall_base > 2))
    
    # Wind speed
    wind = np.maximum(0, rng.normal(8, 3, n_days))
    
    # Solar radiation
    solar = np.maximum(0, 5.5 + 1.5 * season + rng.normal(0, 0.5, n_days))
    
    # Soil moisture: autoregressive + driven by rainfall, evaporation
    soil_moisture = np.zeros(n_days)
    soil_moisture[0] = 35.0  # Initial moisture
    
    for i in range(1, n_days):
        # Moisture gain from rainfall
        gain = rainfall[i] * 0.3
        # Moisture loss from evapotranspiration (temp-dependent)
        loss = (temp[i] / 30) * 2.5 + wind[i] * 0.1
        # Autoregressive component
        soil_moisture[i] = soil_moisture[i - 1] * 0.92 + gain - loss + rng.normal(0, 1)
        soil_moisture[i] = np.clip(soil_moisture[i], 5, 70)
    
    data = np.column_stack([temp, humidity, rainfall, wind, solar, soil_moisture])
    return data


def create_sequences(
    data: np.ndarray,
    seq_len: int = SEQUENCE_LENGTH,
    horizons: List[int] = FORECAST_HORIZONS,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create sliding window sequences from time-series data.
    
    Args:
        data: (T, F) full time series
        seq_len: Length of input sequence
        horizons: List of forecast horizons (days ahead)
        
    Returns:
        sequences: (N, seq_len, F)
        targets: (N, len(horizons)) - soil moisture at each horizon
    """
    max_horizon = max(horizons)
    n_samples = len(data) - seq_len - max_horizon
    
    sequences = []
    targets = []
    
    moisture_idx = FEATURE_NAMES.index("soil_moisture_pct")
    
    for i in range(n_samples):
        seq = data[i:i + seq_len]
        target = [data[i + seq_len + h - 1, moisture_idx] for h in horizons]
        sequences.append(seq)
        targets.append(target)
    
    return np.array(sequences), np.array(targets)


def train_lstm_forecaster(
    n_days: int = 2000,
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 1e-3,
    patience: int = 8,
    device: torch.device = None,
    seed: int = 42,
) -> Dict:
    """
    Train the LSTM forecaster on synthetic time-series data.
    
    Uses time-aware split: first 70% train, next 15% val, last 15% test.
    """
    device = device or DEVICE
    print(f"[LSTM Training] Device: {device}")

    # ── Generate data ─────────────────────────────────────────
    raw_data = generate_synthetic_timeseries(n_days=n_days, seed=seed)
    
    # Normalize features
    means = raw_data.mean(axis=0)
    stds = raw_data.std(axis=0) + 1e-8
    normalized = (raw_data - means) / stds
    
    sequences, targets = create_sequences(normalized)
    
    # Normalize targets separately (soil moisture predictions)
    moisture_idx = FEATURE_NAMES.index("soil_moisture_pct")
    target_mean = means[moisture_idx]
    target_std = stds[moisture_idx]
    
    # Time-aware split (no shuffling!)
    n = len(sequences)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    
    train_seqs, train_tgts = sequences[:n_train], targets[:n_train]
    val_seqs, val_tgts = sequences[n_train:n_train + n_val], targets[n_train:n_train + n_val]
    test_seqs, test_tgts = sequences[n_train + n_val:], targets[n_train + n_val:]
    
    print(f"[LSTM Training] Train: {len(train_seqs)}, Val: {len(val_seqs)}, Test: {len(test_seqs)}")
    
    train_ds = SoilMoistureDataset(train_seqs, train_tgts)
    val_ds = SoilMoistureDataset(val_seqs, val_tgts)
    test_ds = SoilMoistureDataset(test_seqs, test_tgts)
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, pin_memory=True)
    
    # ── Model ─────────────────────────────────────────────────
    model = LSTMForecaster().to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)
    
    history = {"train": [], "val": [], "test": {}}
    best_val_loss = float("inf")
    no_improve = 0
    checkpoint_path = os.path.join(CHECKPOINTS_DIR, "lstm_forecaster.pt")
    
    # ── Training loop ─────────────────────────────────────────
    for epoch in range(1, epochs + 1):
        t0 = time.time()
        
        # Train
        model.train()
        train_loss = 0.0
        for seqs, tgts in train_loader:
            seqs = seqs.to(device, non_blocking=True)
            tgts = tgts.to(device, non_blocking=True)
            
            optimizer.zero_grad(set_to_none=True)
            preds = model(seqs)
            loss = criterion(preds, tgts)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * seqs.size(0)
        
        train_loss /= len(train_ds)
        
        # Validate
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for seqs, tgts in val_loader:
                seqs = seqs.to(device, non_blocking=True)
                tgts = tgts.to(device, non_blocking=True)
                preds = model(seqs)
                val_loss += criterion(preds, tgts).item() * seqs.size(0)
        val_loss /= len(val_ds)
        
        scheduler.step(val_loss)
        elapsed = time.time() - t0
        
        record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(val_loss, 6),
            "lr": optimizer.param_groups[0]["lr"],
            "time_s": round(elapsed, 1),
        }
        history["train"].append(record)
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{epochs} | Train Loss: {train_loss:.6f} | "
                  f"Val Loss: {val_loss:.6f} | {elapsed:.1f}s")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_loss": best_val_loss,
                "epoch": epoch,
                "means": means.tolist(),
                "stds": stds.tolist(),
                "horizons": FORECAST_HORIZONS,
            }, checkpoint_path)
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"  Early stopping at epoch {epoch}")
                break
    
    # ── Test evaluation ───────────────────────────────────────
    print("\n═══ LSTM Test Evaluation ═══")
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    all_preds = []
    all_tgts = []
    with torch.no_grad():
        for seqs, tgts in test_loader:
            seqs = seqs.to(device, non_blocking=True)
            preds = model(seqs)
            all_preds.append(preds.cpu().numpy())
            all_tgts.append(tgts.cpu().numpy())
    
    all_preds = np.concatenate(all_preds)
    all_tgts = np.concatenate(all_tgts)
    
    # Denormalize predictions
    preds_denorm = all_preds * target_std + target_mean
    tgts_denorm = all_tgts * target_std + target_mean
    
    # Compute naive baseline (last known value)
    naive_preds = np.tile(test_seqs[:, -1, moisture_idx:moisture_idx + 1] * target_std + target_mean,
                          (1, len(FORECAST_HORIZONS)))
    
    test_metrics = {}
    for i, h in enumerate(FORECAST_HORIZONS):
        mae_lstm = float(np.mean(np.abs(preds_denorm[:, i] - tgts_denorm[:, i])))
        rmse_lstm = float(np.sqrt(np.mean((preds_denorm[:, i] - tgts_denorm[:, i]) ** 2)))
        mae_naive = float(np.mean(np.abs(naive_preds[:, i] - tgts_denorm[:, i])))
        
        test_metrics[f"{h}d"] = {
            "lstm_mae": round(mae_lstm, 3),
            "lstm_rmse": round(rmse_lstm, 3),
            "naive_mae": round(mae_naive, 3),
            "skill_score": round(1 - mae_lstm / max(mae_naive, 1e-8), 4),
        }
        print(f"  {h:2d}-day: LSTM MAE={mae_lstm:.3f}, Naive MAE={mae_naive:.3f}, "
              f"Skill={test_metrics[f'{h}d']['skill_score']:.4f}")
    
    history["test"] = test_metrics
    
    # Save metrics
    report_path = os.path.join(REPORTS_DIR, "timeseries_metrics.json")
    with open(report_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"\n[LSTM Training] Metrics saved to {report_path}")
    
    return history


class LSTMPredictor:
    """
    Inference wrapper for the trained LSTM forecaster.
    """

    def __init__(self, checkpoint_path: Optional[str] = None, device: torch.device = None):
        self.device = device or DEVICE
        self.checkpoint_path = checkpoint_path or os.path.join(CHECKPOINTS_DIR, "lstm_forecaster.pt")
        
        self.model = LSTMForecaster().to(self.device)
        self.means = None
        self.stds = None
        self._loaded = False
        
        if os.path.isfile(self.checkpoint_path):
            ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(ckpt["model_state_dict"])
            self.means = np.array(ckpt["means"])
            self.stds = np.array(ckpt["stds"])
            self._loaded = True
            print(f"[LSTMPredictor] Loaded checkpoint: {self.checkpoint_path}")
        
        self.model.eval()

    def predict(self, sequence: np.ndarray) -> Dict:
        """
        Predict future soil moisture from a historical sequence.
        
        Args:
            sequence: (L, F) array of L days × F features
                      Features: temp, humidity, rainfall, wind, solar, soil_moisture
                      
        Returns:
            Dictionary with forecasted moisture at each horizon.
        """
        if not self._loaded:
            return {"error": "No trained model. Run train_lstm_forecaster() first."}
        
        # Normalize
        normalized = (sequence - self.means) / (self.stds + 1e-8)
        
        # Ensure correct sequence length
        if len(normalized) > SEQUENCE_LENGTH:
            normalized = normalized[-SEQUENCE_LENGTH:]
        elif len(normalized) < SEQUENCE_LENGTH:
            # Pad with zeros
            pad = np.zeros((SEQUENCE_LENGTH - len(normalized), N_INPUT_FEATURES))
            normalized = np.vstack([pad, normalized])
        
        # Predict
        x = torch.FloatTensor(normalized).unsqueeze(0).to(self.device)
        with torch.no_grad():
            pred = self.model(x).cpu().numpy()[0]
        
        # Denormalize
        moisture_idx = FEATURE_NAMES.index("soil_moisture_pct")
        pred_denorm = pred * self.stds[moisture_idx] + self.means[moisture_idx]
        
        forecasts = {}
        for i, h in enumerate(FORECAST_HORIZONS):
            val = float(np.clip(pred_denorm[i], 5, 70))
            forecasts[f"{h}_day"] = {
                "soil_moisture_pct": round(val, 2),
                "water_stress": "high" if val < 20 else ("moderate" if val < 30 else "low"),
            }
        
        return {
            "current_moisture_pct": round(float(sequence[-1, moisture_idx]), 2),
            "forecasts": forecasts,
            "model": "LSTM (2-layer, hidden=64)",
            "horizons_days": FORECAST_HORIZONS,
        }


if __name__ == "__main__":
    train_lstm_forecaster()
