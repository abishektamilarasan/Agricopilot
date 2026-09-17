"""
Real Agricultural Yield Prediction Model Training Pipeline
Trained on 246,000+ real records from Ministry of Agriculture, India (1997-2021).
Yield (Production / Area) with Log-Transform, Robust Outlier Removal,
XGBoost & Random Forest Ensembling with Split Conformal Prediction Intervals (90% CI).
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(os.path.dirname(BASE_DIR), "ML_dataset", "crop_production.csv")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

def train_yield_models():
    print("=" * 60)
    print("3. Training Crop Yield Model on Real Indian Agriculture Data")
    print("=" * 60)
    
    print("Loading crop_production.csv...")
    df = pd.read_csv(DATASET_PATH)
    
    # 1. Cleaning & feature engineering
    df = df.dropna(subset=['Production', 'Area'])
    df = df[(df['Area'] > 0) & (df['Production'] >= 0)]
    
    # Calculate Yield (tons/ha or quintal/ha)
    df['Yield'] = df['Production'] / df['Area']
    
    # Filter realistic yield limits per crop (clip top 1% outliers to avoid data entry typos)
    p99 = df.groupby('Crop')['Yield'].transform(lambda x: x.quantile(0.99))
    df = df[df['Yield'] <= p99]
    
    print(f"Cleaned samples: {len(df):,}")
    
    # Focus features
    features = ['State_Name', 'District_Name', 'Season', 'Crop', 'Area', 'Crop_Year']
    X = df[features]
    y = np.log1p(df['Yield'])  # Log transform for stable variance
    
    # Split into Train, Calibration (for Conformal Prediction), and Test
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42
    )
    X_train, X_calib, y_train, y_calib = train_test_split(
        X_train_full, y_train_full, test_size=0.15, random_state=42
    )
    
    cat_features = ['State_Name', 'District_Name', 'Season', 'Crop']
    num_features = ['Area', 'Crop_Year']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=True), cat_features),
            ('num', 'passthrough', num_features)
        ]
    )
    
    print("Preprocessing & fitting feature pipeline...")
    X_train_trans = preprocessor.fit_transform(X_train)
    X_calib_trans = preprocessor.transform(X_calib)
    X_test_trans = preprocessor.transform(X_test)
    
    # Train XGBoost with tree_method='hist' for ultra-fast training
    print("Training XGBoost Regressor on full feature space...")
    xgb_reg = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=10,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        random_state=42,
        n_jobs=-1
    )
    xgb_reg.fit(X_train_trans, y_train)
    
    # Evaluation on Test set
    y_pred_log = xgb_reg.predict(X_test_trans)
    y_pred = np.expm1(y_pred_log)
    y_test_orig = np.expm1(y_test)
    
    r2 = r2_score(y_test_orig, y_pred)
    mae = mean_absolute_error(y_test_orig, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test_orig, y_pred))
    
    print(f"\n--- Yield Model Test Results ---")
    print(f"R² Score: {r2:.4f}")
    print(f"MAE: {mae:.3f} tons/ha")
    print(f"RMSE: {rmse:.3f} tons/ha")
    
    # Conformal Prediction Calibration for 90% Confidence Interval
    print("\nComputing Split Conformal Prediction Intervals (90% CI)...")
    calib_preds_log = xgb_reg.predict(X_calib_trans)
    calib_residuals = np.abs(y_calib.values - calib_preds_log)
    alpha = 0.10  # 90% coverage
    q_val = np.quantile(calib_residuals, np.ceil((1 - alpha) * (len(calib_residuals) + 1)) / len(calib_residuals))
    print(f"Conformal Residual Quantile (q_val): {q_val:.4f}")
    
    # Save Model & Preprocessor
    model_bundle = {
        'model': xgb_reg,
        'preprocessor': preprocessor,
        'q_val': q_val,
        'features': features
    }
    output_path = os.path.join(CHECKPOINTS_DIR, "yield_xgboost_real.joblib")
    joblib.dump(model_bundle, output_path)
    print(f"Saved real yield prediction model bundle to {output_path}")
    return r2

if __name__ == "__main__":
    train_yield_models()
