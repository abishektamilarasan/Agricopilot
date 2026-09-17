"""
Disease Detection Inference Module

Provides a high-level API for running disease predictions on crop images,
including top-k classification with probabilities and Grad-CAM explanations.

Usage:
    from ml.disease.inference import DiseasePredictor
    predictor = DiseasePredictor()
    result = predictor.predict_from_file("path/to/leaf.jpg")
"""

import io
import os
import json
from typing import Dict, List, Optional, Union

import numpy as np
from PIL import Image

import torch
import torch.nn.functional as F

from ml import DEVICE, CHECKPOINTS_DIR
from ml.disease.dataset import (
    DISEASE_CLASSES, IDX_TO_CLASS, NUM_CLASSES, VAL_TRANSFORM,
)
from ml.disease.model import DiseaseClassifier
from ml.disease.gradcam import GradCAM


# ── Disease action recommendations ───────────────────────────
DISEASE_ACTIONS = {
    "healthy": {
        "severity": "none",
        "action": "No action needed. Continue regular monitoring.",
        "prevention": "Maintain proper irrigation, spacing, and nutrient balance.",
    },
    "leaf_blast": {
        "severity": "high",
        "action": "Apply tricyclazole (0.6 g/L) or isoprothiolane. Remove infected leaves.",
        "prevention": "Avoid excess nitrogen. Maintain proper field drainage. Use resistant varieties.",
    },
    "bacterial_blight": {
        "severity": "high",
        "action": "Apply copper oxychloride (3 g/L). Drain standing water. Avoid excess nitrogen.",
        "prevention": "Use certified disease-free seeds. Balanced NPK fertilization.",
    },
    "brown_spot": {
        "severity": "moderate",
        "action": "Apply mancozeb (2.5 g/L) or propiconazole. Ensure adequate potassium.",
        "prevention": "Balanced fertilization especially K. Avoid water stress.",
    },
    "rust": {
        "severity": "moderate",
        "action": "Apply propiconazole or tebuconazole. Remove severely infected plants.",
        "prevention": "Use resistant cultivars. Ensure good air circulation.",
    },
}


class DiseasePredictor:
    """
    High-level disease prediction interface.
    
    Loads a trained checkpoint (or creates an untrained model for demo)
    and provides predict methods with Grad-CAM explanations.
    """

    def __init__(self, checkpoint_path: Optional[str] = None, class_json_path: Optional[str] = None, device: torch.device = None):
        self.device = device or DEVICE
        
        # Check for 38-class PlantVillage checkpoint first, then fallback to disease_best.pt
        pv_ckpt = os.path.join(CHECKPOINTS_DIR, "disease_plantvillage_best.pt")
        legacy_ckpt = os.path.join(CHECKPOINTS_DIR, "disease_best.pt")
        
        self.checkpoint_path = checkpoint_path or (pv_ckpt if os.path.isfile(pv_ckpt) else legacy_ckpt)
        
        # Determine number of classes and mapping
        self.class_names = DISEASE_CLASSES
        class_json = class_json_path or os.path.join(CHECKPOINTS_DIR, "plantvillage_classes.json")
        if os.path.isfile(class_json):
            with open(class_json, "r") as f:
                self.class_names = json.load(f)
                
        self.num_classes = len(self.class_names)
        self.idx_to_class = {i: c for i, c in enumerate(self.class_names)}
        
        # Load model
        from torchvision import models
        weights = models.EfficientNet_V2_S_Weights.DEFAULT if not os.path.isfile(self.checkpoint_path) else None
        self.model = models.efficientnet_v2_s(weights=weights)
        in_features = self.model.classifier[1].in_features
        self.model.classifier = torch.nn.Sequential(
            torch.nn.Dropout(p=0.3, inplace=True),
            torch.nn.Linear(in_features, 512),
            torch.nn.BatchNorm1d(512),
            torch.nn.SiLU(inplace=True),
            torch.nn.Dropout(p=0.2),
            torch.nn.Linear(512, self.num_classes)
        )
        
        if os.path.isfile(self.checkpoint_path):
            ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
            state_dict = ckpt.get("model_state_dict", ckpt)
            # The training script wraps the model in a class with self.backbone,
            # so saved keys are prefixed with "backbone.". Strip that prefix
            # to match our bare efficientnet_v2_s() model.
            cleaned = {}
            for k, v in state_dict.items():
                new_key = k.replace("backbone.", "", 1) if k.startswith("backbone.") else k
                cleaned[new_key] = v
            self.model.load_state_dict(cleaned)
            self._trained = True
            print(f"[DiseasePredictor] Loaded trained checkpoint: {self.checkpoint_path} ({self.num_classes} classes)")
        else:
            self._trained = False
            print("[DiseasePredictor] No checkpoint found. Initialized backbone.")
        
        self.model.to(self.device)
        self.model.eval()
        
        # Initialize Grad-CAM
        self.gradcam = GradCAM(self.model)
        self.transform = VAL_TRANSFORM

    @property
    def is_trained(self) -> bool:
        return self._trained

    def predict_from_file(self, image_path: str, top_k: int = 3) -> Dict:
        """
        Predict disease from an image file path.
        
        Returns dict with:
          - predictions: list of {class, probability}
          - gradcam_overlay_base64: base64 PNG of Grad-CAM overlay
          - disease_info: action recommendations for top prediction
        """
        img = Image.open(image_path).convert("RGB")
        return self.predict(img, top_k=top_k)

    def predict_from_bytes(self, image_bytes: bytes, top_k: int = 3) -> Dict:
        """Predict from raw image bytes (e.g., from file upload)."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return self.predict(img, top_k=top_k)

    def predict(self, image: Image.Image, top_k: int = 3) -> Dict:
        """
        Run prediction + Grad-CAM on a PIL Image.
        
        Args:
            image: PIL Image (RGB)
            top_k: Number of top predictions to return
            
        Returns:
            Prediction result dictionary
        """
        # Preprocess
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)
        
        # Forward pass
        with torch.no_grad():
            logits = self.model(input_tensor)
            probs = F.softmax(logits, dim=1)[0]
        
        # Top-k predictions
        top_probs, top_indices = probs.topk(min(top_k, self.num_classes))
        predictions = []
        for prob, idx in zip(top_probs.cpu().numpy(), top_indices.cpu().numpy()):
            cls_name = self.idx_to_class[idx]
            predictions.append({
                "class": cls_name,
                "class_label": cls_name.replace("___", " - ").replace("_", " ").title(),
                "probability": round(float(prob), 4),
            })
        
        top_class = predictions[0]["class"]
        top_confidence = predictions[0]["probability"]
        
        # Grad-CAM
        gradcam_result = self.gradcam.generate_base64(
            input_tensor, image, target_class=top_indices[0].item()
        )
        
        # Disease action info (generic fallback for 38 classes)
        disease_info = DISEASE_ACTIONS.get(top_class, {
            "severity": "none" if "healthy" in top_class.lower() else "moderate",
            "action": "Maintain optimal irrigation and check crop health." if "healthy" in top_class.lower() else f"Apply recommended fungicide/bactericide for {top_class.replace('___', ' ').replace('_', ' ')}.",
            "prevention": "Ensure good ventilation, crop rotation, and balanced fertilization."
        })
        
        return {
            "predictions": predictions,
            "top_prediction": {
                "class": top_class,
                "label": top_class.replace("___", " - ").replace("_", " ").title(),
                "confidence": top_confidence,
            },
            "disease_info": disease_info,
            "gradcam": {
                "overlay_base64": gradcam_result["heatmap_overlay_base64"],
                "heatmap_base64": gradcam_result["heatmap_raw_base64"],
            },
            "model_info": {
                "model": "EfficientNetV2-S",
                "trained": self._trained,
                "device": str(self.device),
                "classes": self.class_names,
            },
        }

    def batch_predict(self, images: List[Image.Image]) -> List[Dict]:
        """Predict on a batch of images."""
        return [self.predict(img) for img in images]
