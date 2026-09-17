"""
Grad-CAM (Gradient-weighted Class Activation Mapping) Implementation

Generates visual explanations for CNN predictions by highlighting the regions
of the input image that most influence the model's decision.

Reference: Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks
via Gradient-based Localization", ICCV 2017.
"""

import io
import base64
from typing import Optional, Tuple

import numpy as np
from PIL import Image

import torch
import torch.nn.functional as F

from ml.disease.model import DiseaseClassifier


class GradCAM:
    """
    Grad-CAM explainability for the disease classification model.
    
    Usage:
        model = DiseaseClassifier(...)
        gradcam = GradCAM(model)
        heatmap, pred_class, confidence = gradcam.generate(input_tensor)
        overlay = gradcam.overlay_heatmap(original_image, heatmap)
    """
    
    def __init__(self, model: torch.nn.Module, target_layer: Optional[torch.nn.Module] = None):
        self.model = model
        self.model.eval()
        
        # Hook into the target layer (last conv by default)
        if target_layer:
            self.target_layer = target_layer
        elif hasattr(model, "get_last_conv_layer"):
            self.target_layer = model.get_last_conv_layer()
        elif hasattr(model, "features"):
            self.target_layer = model.features[-1]
        elif hasattr(model, "backbone") and hasattr(model.backbone, "features"):
            self.target_layer = model.backbone.features[-1]
        else:
            # Fallback to the last convolutional layer found in model
            conv_layers = [m for m in model.modules() if isinstance(m, torch.nn.Conv2d)]
            self.target_layer = conv_layers[-1] if conv_layers else None
            
        self._gradients = None
        self._activations = None
        
        # Register hooks
        self._forward_hook = self.target_layer.register_forward_hook(self._save_activation)
        self._backward_hook = self.target_layer.register_full_backward_hook(self._save_gradient)
    
    def _save_activation(self, module, input, output):
        """Forward hook: save feature map activations."""
        self._activations = output.detach()
    
    def _save_gradient(self, module, grad_input, grad_output):
        """Backward hook: save gradients."""
        self._gradients = grad_output[0].detach()
    
    def generate(
        self,
        input_tensor: torch.Tensor,
        target_class: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, float]:
        """
        Generate Grad-CAM heatmap for the input.
        
        Args:
            input_tensor: Preprocessed image tensor (1, 3, H, W)
            target_class: Class index to explain. If None, uses predicted class.
            
        Returns:
            heatmap: numpy array (H, W) with values in [0, 1]
            predicted_class: integer class index
            confidence: probability of the predicted class
        """
        if input_tensor.dim() == 3:
            input_tensor = input_tensor.unsqueeze(0)
        
        input_tensor = input_tensor.to(next(self.model.parameters()).device)
        input_tensor.requires_grad_(True)
        
        # Forward pass
        output = self.model(input_tensor)
        probabilities = F.softmax(output, dim=1)
        
        predicted_class = output.argmax(dim=1).item()
        confidence = probabilities[0, predicted_class].item()
        
        # Use target class or predicted class
        if target_class is None:
            target_class = predicted_class
        
        # Backward pass for target class
        self.model.zero_grad()
        class_score = output[0, target_class]
        class_score.backward(retain_graph=True)
        
        # Compute Grad-CAM
        gradients = self._gradients[0]  # (C, H, W)
        activations = self._activations[0]  # (C, H, W)
        
        # Global average pooling of gradients → channel weights
        weights = gradients.mean(dim=(1, 2))  # (C,)
        
        # Weighted combination of activation maps
        cam = torch.zeros(activations.shape[1:], device=activations.device)
        for i, w in enumerate(weights):
            cam += w * activations[i]
        
        # ReLU — only positive contributions
        cam = F.relu(cam)
        
        # Normalize to [0, 1]
        if cam.max() > 0:
            cam = cam / cam.max()
        
        # Resize to input dimensions
        cam = cam.unsqueeze(0).unsqueeze(0)  # (1, 1, h, w)
        cam = F.interpolate(cam, size=(input_tensor.shape[2], input_tensor.shape[3]),
                            mode='bilinear', align_corners=False)
        cam = cam.squeeze().cpu().numpy()
        
        return cam, predicted_class, confidence
    
    def overlay_heatmap(
        self,
        original_image: Image.Image,
        heatmap: np.ndarray,
        alpha: float = 0.5,
        colormap: str = "jet",
    ) -> Image.Image:
        """
        Overlay Grad-CAM heatmap on the original image.
        
        Args:
            original_image: PIL Image
            heatmap: (H, W) numpy array in [0, 1]
            alpha: Blending factor (0 = original, 1 = heatmap)
            colormap: Matplotlib colormap name
            
        Returns:
            Blended PIL Image
        """
        import matplotlib.cm as cm
        
        # Resize heatmap to match image
        img_w, img_h = original_image.size
        heatmap_resized = np.array(
            Image.fromarray((heatmap * 255).astype(np.uint8)).resize((img_w, img_h))
        ).astype(np.float32) / 255.0
        
        # Apply colormap
        cmap = cm.get_cmap(colormap)
        heatmap_colored = cmap(heatmap_resized)[:, :, :3]  # Drop alpha channel
        heatmap_colored = (heatmap_colored * 255).astype(np.uint8)
        heatmap_img = Image.fromarray(heatmap_colored)
        
        # Blend
        original_rgb = original_image.convert("RGB")
        blended = Image.blend(original_rgb, heatmap_img, alpha=alpha)
        
        return blended
    
    def generate_base64(
        self,
        input_tensor: torch.Tensor,
        original_image: Image.Image,
        target_class: Optional[int] = None,
    ) -> dict:
        """
        Generate Grad-CAM and return base64-encoded overlay + metadata.
        Suitable for direct API response.
        """
        heatmap, pred_class, confidence = self.generate(input_tensor, target_class)
        overlay = self.overlay_heatmap(original_image, heatmap)
        
        # Encode overlay to base64
        buffer = io.BytesIO()
        overlay.save(buffer, format="PNG")
        b64_overlay = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        # Also encode the raw heatmap
        heatmap_img = Image.fromarray((heatmap * 255).astype(np.uint8))
        buffer2 = io.BytesIO()
        heatmap_img.save(buffer2, format="PNG")
        b64_heatmap = base64.b64encode(buffer2.getvalue()).decode("utf-8")
        
        return {
            "predicted_class": pred_class,
            "confidence": round(confidence, 4),
            "heatmap_overlay_base64": b64_overlay,
            "heatmap_raw_base64": b64_heatmap,
        }
    
    def cleanup(self):
        """Remove hooks to prevent memory leaks."""
        self._forward_hook.remove()
        self._backward_hook.remove()
    
    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
