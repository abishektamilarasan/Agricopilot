"""
PlantVillage EfficientNetV2-S — Resume Training from Epoch 3 to 15
Uses RTX 4050 GPU with mixed precision (AMP).
Resumes from the best checkpoint saved at epoch 3 (98.33% val acc).
Continues progressive unfreezing phases for maximum accuracy.
"""

import os
import sys
import time
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "ML_dataset", "PlantVillage-Dataset-master", "raw", "color")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")

IMG_SIZE = 224
BATCH_SIZE = 64
START_EPOCH = 4       # resume from after epoch 3
TOTAL_EPOCHS = 15     # train up to epoch 15

# Stronger augmentation for later epochs
TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
    transforms.RandomCrop(IMG_SIZE),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(25),
    transforms.RandomAffine(degrees=0, translate=(0.05, 0.05), scale=(0.95, 1.05)),
    transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.25, hue=0.08),
    transforms.RandomGrayscale(p=0.02),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.1, scale=(0.02, 0.15)),
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
    """Same architecture as original training script."""
    def __init__(self, num_classes=38):
        super().__init__()
        self.backbone = models.efficientnet_v2_s(weights=None)
        in_features = self.backbone.classifier[1].in_features
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


def main():
    print("=" * 65)
    print(f"PlantVillage - RESUME Training (Epochs {START_EPOCH}-{TOTAL_EPOCHS})")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"Device: {DEVICE}")
    print("=" * 65)

    # Load dataset
    full_dataset = datasets.ImageFolder(DATA_DIR)
    classes = full_dataset.classes
    num_classes = len(classes)
    print(f"Dataset: {len(full_dataset):,} images, {num_classes} classes")

    # Same split as original (seed=42)
    train_size = int(0.80 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_subset, val_subset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_data = TransformedDataset(train_subset, TRAIN_TRANSFORM)
    val_data = TransformedDataset(val_subset, VAL_TRANSFORM)

    train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=0, pin_memory=True)

    # Build model and load checkpoint
    model = EfficientNetV2PlantDoctor(num_classes).to(DEVICE)
    ckpt_path = os.path.join(CHECKPOINTS_DIR, "disease_plantvillage_best.pt")
    ckpt = torch.load(ckpt_path, map_location=DEVICE, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    best_val_acc = ckpt.get("val_acc", 0.0)
    print(f"Resumed from epoch {ckpt.get('epoch', '?')} | Best Val Acc: {best_val_acc:.2f}%")

    # Since we're starting at epoch 4, we're in Phase 2 (progressive unfreezing)
    # Unfreeze top 3 backbone stages + classifier
    print("\n[Phase 2] Progressive unfreezing - top 3 backbone stages...")
    for param in model.backbone.features.parameters():
        param.requires_grad = False
    for block in model.backbone.features[-3:]:
        for param in block.parameters():
            param.requires_grad = True
    for param in model.backbone.classifier.parameters():
        param.requires_grad = True

    criterion = nn.CrossEntropyLoss(label_smoothing=0.08)
    scaler = torch.amp.GradScaler('cuda')

    # Differential LR for phase 2
    optimizer = torch.optim.AdamW([
        {'params': model.backbone.features[-3:].parameters(), 'lr': 1e-4},
        {'params': model.backbone.classifier.parameters(), 'lr': 3e-4}
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=TOTAL_EPOCHS - START_EPOCH + 1, eta_min=1e-6)

    best_checkpoint = os.path.join(CHECKPOINTS_DIR, "disease_plantvillage_best.pt")

    for epoch in range(START_EPOCH, TOTAL_EPOCHS + 1):
        # Phase 3: Full backbone fine-tuning from epoch 6
        if epoch == 6:
            print("\n[Phase 3] Full backbone fine-tuning with small learning rate...")
            for param in model.backbone.features.parameters():
                param.requires_grad = True
            optimizer = torch.optim.AdamW([
                {'params': model.backbone.features.parameters(), 'lr': 2e-5},
                {'params': model.backbone.classifier.parameters(), 'lr': 8e-5}
            ], weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
                optimizer, T_0=3, T_mult=2, eta_min=1e-7
            )

        # Phase 4: Very fine-grained tuning
        if epoch == 10:
            print("\n[Phase 4] Ultra-fine tuning with tiny LR...")
            optimizer = torch.optim.AdamW([
                {'params': model.backbone.features.parameters(), 'lr': 5e-6},
                {'params': model.backbone.classifier.parameters(), 'lr': 2e-5}
            ], weight_decay=2e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=TOTAL_EPOCHS - 9, eta_min=1e-7
            )

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
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total_train += targets.size(0)
            train_correct += predicted.eq(targets).sum().item()

            if (batch_idx + 1) % 100 == 0 or (batch_idx + 1) == len(train_loader):
                acc = 100. * train_correct / total_train
                print(f"  Epoch {epoch:02d} [{batch_idx+1}/{len(train_loader)}] "
                      f"Loss: {train_loss/total_train:.4f} | Train Acc: {acc:.2f}%")

        scheduler.step()

        # Validation
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

        print(f"--> Epoch {epoch:02d} | {epoch_time:.1f}s | Val Loss: {val_epoch_loss:.4f} | Val Acc: {val_acc:.2f}%")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_acc': val_acc,
                'classes': classes,
            }, best_checkpoint)
            print(f"  *** NEW BEST: {val_acc:.2f}% saved! ***")

    print("\n" + "=" * 65)
    print(f"TRAINING COMPLETE! Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Model: {best_checkpoint}")
    print("=" * 65)

if __name__ == "__main__":
    main()
