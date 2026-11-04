
import torch
import torch.nn as nn
from torchvision import models

from ml.disease.dataset import NUM_CLASSES


class DiseaseClassifier(nn.Module):
    """
    EfficientNetV2-B0 based plant disease classifier.
    
    Supports:
        - Feature extraction mode (backbone frozen)
        - Full fine-tuning mode (backbone unfrozen)
        - Mixed precision training compatible
    """

    def __init__(self, num_classes: int = NUM_CLASSES, pretrained: bool = True, freeze_backbone: bool = True):
        super().__init__()
        
        # Load pretrained EfficientNetV2-B0
        if pretrained:
            weights = models.EfficientNet_V2_S_Weights.DEFAULT
            self.backbone = models.efficientnet_v2_s(weights=weights)
        else:
            self.backbone = models.efficientnet_v2_s(weights=None)
        
        # Extract the feature dimension from the original classifier
        in_features = self.backbone.classifier[1].in_features  # 1280 for V2-S
        
        # Replace classifier head
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(256, num_classes),
        )
        
        # Optionally freeze backbone
        if freeze_backbone:
            self.freeze_backbone()
    
    def freeze_backbone(self):
        """Freeze all backbone layers (features), only train classifier."""
        for param in self.backbone.features.parameters():
            param.requires_grad = False
    
    def unfreeze_backbone(self, unfreeze_from: int = -3):
        """
        Unfreeze the last N feature blocks for fine-tuning.
        
        Args:
            unfreeze_from: Index from which to unfreeze. -3 means last 3 blocks.
        """
        # First freeze everything
        for param in self.backbone.features.parameters():
            param.requires_grad = False
        
        # Then unfreeze the last N blocks
        blocks = list(self.backbone.features.children())
        for block in blocks[unfreeze_from:]:
            for param in block.parameters():
                param.requires_grad = True
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (B, 3, 224, 224)
            
        Returns:
            Logits tensor of shape (B, NUM_CLASSES)
        """
        return self.backbone(x)
    
    def get_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extract feature maps from the last convolutional layer.
        Used by Grad-CAM.
        
        Args:
            x: Input tensor of shape (B, 3, 224, 224)
            
        Returns:
            Feature maps from the last conv block.
        """
        return self.backbone.features(x)
    
    def get_last_conv_layer(self) -> nn.Module:
        """Return the last convolutional layer for Grad-CAM hooking."""
        return self.backbone.features[-1]


def create_model(
    num_classes: int = NUM_CLASSES,
    pretrained: bool = True,
    freeze_backbone: bool = True,
    device: torch.device = None,
) -> DiseaseClassifier:
    """
    Factory function to create and optionally move model to device.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = DiseaseClassifier(
        num_classes=num_classes,
        pretrained=pretrained,
        freeze_backbone=freeze_backbone,
    )
    return model.to(device)
