"""
Vision API Routes
Integrates the EfficientNetV2 plant disease classification models.
"""

import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ml.disease.inference import DiseasePredictor
from ml import CHECKPOINTS_DIR
from agents.copilot import _call_llm_chat

router = APIRouter()

# Initialize predictors
try:
    predictor_pv = DiseasePredictor()
except Exception as e:
    print(f"[Vision] Failed to initialize PlantVillage Predictor: {e}")
    predictor_pv = None

try:
    indian_ckpt = os.path.join(CHECKPOINTS_DIR, "disease_indian_best.pt")
    indian_json = os.path.join(CHECKPOINTS_DIR, "indian_classes.json")
    if os.path.exists(indian_ckpt) and os.path.exists(indian_json):
        predictor_indian = DiseasePredictor(checkpoint_path=indian_ckpt, class_json_path=indian_json)
    else:
        predictor_indian = None
except Exception as e:
    print(f"[Vision] Failed to initialize Indian Predictor: {e}")
    predictor_indian = None


@router.post("/api/diagnose-disease")
async def diagnose_disease(file: UploadFile = File(...), crop: str = Form(None)):
    """
    Diagnose crop diseases from uploaded leaf images.
    Switches to the Indian Crop model if the selected crop is an Indian specialty.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    indian_crops = ["sugarcane", "wheat", "potato", "corn", "rice"]
    try:
        content = await file.read()
        res_pv = predictor_pv.predict_from_bytes(content, top_k=3) if predictor_pv else None
        res_ind = predictor_indian.predict_from_bytes(content, top_k=3) if predictor_indian else None

        if res_pv and res_ind:
            conf_pv = res_pv["top_prediction"]["confidence"]
            conf_ind = res_ind["top_prediction"]["confidence"]
            # Confidence-first selection: if PlantVillage has high certainty (>80%) for specialized crops like blueberry, apple, grape, tomato, peach, don't force Indian 17-class model
            if conf_pv >= 0.80 and conf_pv > conf_ind:
                result = res_pv
            elif crop and crop.lower() in indian_crops:
                result = res_ind if conf_ind >= (conf_pv - 0.15) else res_pv
            else:
                result = res_pv if conf_pv >= conf_ind else res_ind
        elif res_pv:
            result = res_pv
        elif res_ind:
            result = res_ind
        else:
            raise HTTPException(status_code=500, detail="Vision models failed.")

        
        disease_name = result["top_prediction"]["label"]
        crop_name = crop if crop else "the crop"
        prompt = f"The crop '{crop_name}' has been diagnosed with '{disease_name}' with {result['top_prediction']['confidence']*100:.1f}% confidence. Provide a short, actionable, and specific recommendation for treatment and prevention. Use bullet points."
        try:
            ai_recommendation = await _call_llm_chat(prompt)
        except Exception as llm_e:
            print(f"[Vision] LLM error: {llm_e}")
            ai_recommendation = result.get("disease_info", {}).get("action", "No action needed.")
            
        return {
            "status": "success",
            "disease_name": disease_name,
            "confidence": result["top_prediction"]["confidence"],
            "recommendation": ai_recommendation,
            "source": f"Local ML - {result['model_info']['model']}",
            "gradcam": result["gradcam"],
            "all_predictions": result["predictions"],
        }
    except Exception as e:
        print(f"[Vision] Error classifying image: {e}")
        raise HTTPException(status_code=500, detail=f"Image classification failed: {str(e)}")
