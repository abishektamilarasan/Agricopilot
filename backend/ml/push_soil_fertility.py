import pandas as pd
import numpy as np

def add_features(d):
    X = d.copy()
    eps = 1e-4
    X['N_P_ratio'] = X['N'] / (X['P'] + eps)
    X['N_K_ratio'] = X['N'] / (X['K'] + eps)
    X['P_K_ratio'] = X['P'] / (X['K'] + eps)
    X['N_P_prod'] = X['N'] * X['P']
    X['NPK_sum'] = X['N'] + X['P'] + X['K']
    X['EC_OC'] = X['EC'] * X['OC']
    X['pH_dev'] = np.abs(X['pH'] - 7.0)
    X['pH_OC'] = X['pH'] * X['OC']
    X['micro_sum'] = X['Zn'] + X['Fe'] + X['Cu'] + X['Mn'] + X['B']
    X['Fe_Mn_ratio'] = X['Fe'] / (X['Mn'] + eps)
    X['Zn_Cu_ratio'] = X['Zn'] / (X['Cu'] + eps)
    X['macro_micro_ratio'] = X['NPK_sum'] / (X['micro_sum'] + eps)
    X['N_score'] = pd.cut(X['N'], bins=[-np.inf, 200, 280, np.inf], labels=[0, 1, 2]).astype(float)
    X['P_score'] = pd.cut(X['P'], bins=[-np.inf, 10, 25, np.inf], labels=[0, 1, 2]).astype(float)
    X['fertility_composite'] = X['N_score'] * 0.6 + X['P_score'] * 0.4
    if 'Output' in X.columns:
        return X.drop(columns=['Output'])
    return X

class SoilFertilityPredictorPipeline:
    def __init__(self, model_obj):
        self.model = model_obj
    def predict(self, df_raw):
        feats = add_features(df_raw)
        return self.model.predict(feats)
    def predict_proba(self, df_raw):
        feats = add_features(df_raw)
        return self.model.predict_proba(feats)
