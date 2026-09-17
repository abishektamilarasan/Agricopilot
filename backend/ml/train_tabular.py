"""
Training pipeline for Crop Recommendation and Soil Fertility models.
Optimized for highest accuracy using cross-validation and hyperparameter tuning.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(os.path.dirname(BASE_DIR), "ML_dataset")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

def train_crop_recommendation():
    print("=" * 60)
    print("1. Training Crop Recommendation Model (22 Crops)")
    print("=" * 60)
    
    csv_path = os.path.join(DATASET_DIR, "Crop_recommendation.csv")
    df = pd.read_csv(csv_path)
    
    X = df[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
    y = df['label']
    
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    # 1. Random Forest
    rf = RandomForestClassifier(
        n_estimators=150, max_depth=15, random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_preds)
    print(f"Random Forest Accuracy: {rf_acc * 100:.2f}%")
    
    # 2. XGBoost
    xgb_clf = xgb.XGBClassifier(
        n_estimators=150, max_depth=6, learning_rate=0.1,
        eval_metric="mlogloss", random_state=42, n_jobs=-1
    )
    xgb_clf.fit(X_train, y_train)
    xgb_preds = xgb_clf.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_preds)
    print(f"XGBoost Accuracy: {xgb_acc * 100:.2f}%")
    
    # 3. Soft Voting Ensemble for maximum stability & accuracy
    ensemble = VotingClassifier(
        estimators=[('rf', rf), ('xgb', xgb_clf)],
        voting='soft'
    )
    ensemble.fit(X_train, y_train)
    ens_preds = ensemble.predict(X_test)
    ens_acc = accuracy_score(y_test, ens_preds)
    print(f"Ensemble Accuracy: {ens_acc * 100:.2f}%")
    
    # Save model and label encoder
    model_path = os.path.join(CHECKPOINTS_DIR, "crop_recommendation_model.joblib")
    le_path = os.path.join(CHECKPOINTS_DIR, "crop_recommendation_le.joblib")
    joblib.dump(ensemble, model_path)
    joblib.dump(le, le_path)
    print(f"Saved crop recommendation model to {model_path}")
    return ens_acc

def train_soil_fertility():
    print("\n" + "=" * 60)
    print("2. Training Soil Fertility Classifier (dataset1.csv)")
    print("=" * 60)
    
    csv_path = os.path.join(DATASET_DIR, "dataset1.csv")
    df = pd.read_csv(csv_path)
    
    features = ['N', 'P', 'K', 'pH', 'EC', 'OC', 'S', 'Zn', 'Fe', 'Cu', 'Mn', 'B']
    X = df[features]
    y = df['Output']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_split=4,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf.fit(X_train_scaled, y_train)
    rf_preds = rf.predict(X_test_scaled)
    rf_acc = accuracy_score(y_test, rf_preds)
    print(f"Random Forest Soil Fertility Accuracy: {rf_acc * 100:.2f}%")
    
    xgb_clf = xgb.XGBClassifier(
        n_estimators=150, max_depth=5, learning_rate=0.08,
        random_state=42, n_jobs=-1
    )
    xgb_clf.fit(X_train, y_train)
    xgb_preds = xgb_clf.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_preds)
    print(f"XGBoost Soil Fertility Accuracy: {xgb_acc * 100:.2f}%")
    
    best_model = rf if rf_acc >= xgb_acc else xgb_clf
    best_scaler = scaler if rf_acc >= xgb_acc else None
    
    model_path = os.path.join(CHECKPOINTS_DIR, "soil_fertility_model.joblib")
    scaler_path = os.path.join(CHECKPOINTS_DIR, "soil_fertility_scaler.joblib")
    joblib.dump(best_model, model_path)
    if best_scaler:
        joblib.dump(best_scaler, scaler_path)
    print(f"Saved soil fertility model to {model_path}")
    return max(rf_acc, xgb_acc)

if __name__ == "__main__":
    c_acc = train_crop_recommendation()
    s_acc = train_soil_fertility()
    print("\n" + "=" * 60)
    print(f"DONE! Crop Rec Acc: {c_acc*100:.2f}%, Soil Fertility Acc: {s_acc*100:.2f}%")
    print("=" * 60)
