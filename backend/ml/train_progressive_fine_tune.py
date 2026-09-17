"""
PlantVillage 38-Class EfficientNetV2 Progressive Fine-Tuning Pipeline
Architecture & Strategy:
- EfficientNetV2-S pretrained on ImageNet
- Phase 1 (Warmup / Feature Extraction, Epochs 1-2): Backbone frozen, train 512-dim head
- Phase 2 (Progressive Unfreezing, Epochs 3-5): Unfreeze top 3 stages with differential LR (1e-4)
- Phase 3 (Full Backbone Fine-Tuning, Epochs 6-10): All layers unfrozen with Cosine Annealing (3e-5)
- Mixed Precision (torch.amp.autocast) on NVIDIA RTX 4050 GPU
- Integrated Grad-CAM target layer verification
"""

import os
import sys
import time
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models

# Set utf-8 encoding for safe output logging on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "ML_dataset", "PlantVillage-Dataset-master", "raw", "color")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

IMG_SIZE = 224
BATCH_SIZE = 64
EPOCHS = 10

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
    transforms.RandomCrop(IMG_SIZE),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(20),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

class TransformedDataset(torch.utils.data.Dataset):
    def __init__(self, subset, transform):
        self.subset = subset
        self.transform = transform
    def __getitem__(self, idx):
        x, y = self.subset[idx]
        return self.transform(x), y
    def __len__(self):
        return len(self.subset)

class EfficientNetV2PlantDoctor(nn.Module):
    def __init__(self, num_classes=38):
        super().__init__()
        weights = models.EfficientNet_V2_S_Weights.DEFAULT
        self.backbone = models.efficientnet_v2_s(weights=weights)
        in_features = self.backbone.classifier[1].in_features
        
        # High-capacity classification head with SiLU & BatchNorm
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.SiLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(512, num_classes)
        )
        
    def forward(self, x):
        return self.backbone(x)
        
    def get_last_conv_layer(self):
        """Returns the final Conv2dNormActivation block for Grad-CAM."""
        return self.backbone.features[-1]

def main():
    print("=" * 65)
    print(f"PlantVillage Disease Classifier - Progressive Fine-Tuning")
    print(f"Target: NVIDIA RTX 4050 Laptop GPU ({DEVICE})")
    print("=" * 65)
    
    full_dataset = datasets.ImageFolder(DATA_DIR)
    classes = full_dataset.classes
    num_classes = len(classes)
    print(f"Total Dataset Images: {len(full_dataset):,}")
    print(f"Total Classes: {num_classes}")
    
    # Save class mapping
    class_map_path = os.path.join(CHECKPOINTS_DIR, "plantvillage_classes.json")
    with open(class_map_path, "w", encoding="utf-8") as f:
        json.dump(classes, f, indent=2)
    print(f"Saved class mapping to: {class_map_path}")
    
    # 80/20 train/val split
    train_size = int(0.80 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_subset, val_subset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )
    
    train_data = TransformedDataset(train_subset, TRAIN_TRANSFORM)
    val_data = TransformedDataset(val_subset, VAL_TRANSFORM)
    
    train_loader = DataLoader(
        train_data, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=0, pin_memory=True
    )
    val_loader = DataLoader(
        val_data, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=0, pin_memory=True
    )
    
    model = EfficientNetV2PlantDoctor(num_classes).to(DEVICE)
    
    # Phase 1: Freeze all backbone features for warm-up
    print("\n[Phase 1] Freezing feature backbone. Training classifier head...")
    for param in model.backbone.features.parameters():
        param.requires_grad = False
        
    criterion = nn.CrossEntropyLoss(label_smoothing=0.08)
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=6e-4, weight_decay=1e-4
    )
    scaler = torch.amp.GradScaler('cuda')
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
    
    best_val_acc = 0.0
    best_checkpoint = os.path.join(CHECKPOINTS_DIR, "disease_plantvillage_best.pt")
    
    for epoch in range(1, EPOCHS + 1):
        # Progressive Unfreezing Stages
        if epoch == 3:
            print("\n[Phase 2] Progressively unfreezing top feature blocks (Stages 5-7)...")
            for block in model.backbone.features[-3:]:
                for param in block.parameters():
                    param.requires_grad = True
            # Differential learning rate
            optimizer = torch.optim.AdamW([
                {'params': model.backbone.features[-3:].parameters(), 'lr': 1e-4},
                {'params': model.backbone.classifier.parameters(), 'lr': 3e-4}
            ], weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS - 2, eta_min=1e-6)
            
        elif epoch == 6:
            print("\n[Phase 3] Full backbone fine-tuning with small learning rate...")
            for param in model.backbone.features.parameters():
                param.requires_grad = True
            optimizer = torch.optim.AdamW([
                {'params': model.backbone.features.parameters(), 'lr': 3e-5},
                {'params': model.backbone.classifier.parameters(), 'lr': 1e-4}
            ], weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS - 5, eta_min=1e-7)

        start_time = time.time()
        model.train()
        train_loss, train_correct, total_train = 0.0, 0, 0
        
        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs = inputs.to(DEVICE, non_blocking=True)
            targets = targets.to(DEVICE, non_blocking=True)
            optimizer.zero_grad()
            
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
            train_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total_train += targets.size(0)
            train_correct += predicted.eq(targets).sum().item()
            
            if (batch_idx + 1) % 150 == 0 or (batch_idx + 1) == len(train_loader):
                acc = 100. * train_correct / total_train
                print(f"  Epoch {epoch:02d} [{batch_idx+1}/{len(train_loader)}] Loss: {train_loss/total_train:.4f} | Train Acc: {acc:.2f}%")
                
        scheduler.step()
        
        # Validation Evaluation
        model.eval()
        val_loss, val_correct, total_val = 0.0, 0, 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs = inputs.to(DEVICE, non_blocking=True)
                targets = targets.to(DEVICE, non_blocking=True)
                with torch.amp.autocast('cuda'):
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                val_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                total_val += targets.size(0)
                val_correct += predicted.eq(targets).sum().item()
                
        val_acc = 100. * val_correct / total_val
        val_epoch_loss = val_loss / total_val
        epoch_time = time.time() - start_time
        
        print(f"--> Epoch {epoch:02d} Finished in {epoch_time:.1f}s | Val Loss: {val_epoch_loss:.4f} | Val Acc: {val_acc:.2f}%")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_acc': val_acc,
                'classes': classes
            }, best_checkpoint)
            print(f"  [SAVED] New best model saved with Val Acc: {val_acc:.2f}%")
            
    print("\n" + "=" * 65)
    print(f"TRAINING COMPLETE! Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Model saved to: {best_checkpoint}")
    print("=" * 65)

if __name__ == "__main__":
    main()
