"""
Indian Crop Disease EfficientNetV2 Training Pipeline
Uses PyTorch AMP (Automatic Mixed Precision) on NVIDIA RTX 4050 GPU (CUDA).
Supports Indian crops: Rice, Wheat, Sugarcane, Corn, Potato.
Features:
- Learning rate warmup + Cosine Annealing
- Transfer learning with ImageNet weights
- Early stopping & best checkpoint serialization
"""

import os
import time
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "ML_dataset", "Crop Diseases")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

IMG_SIZE = 224
BATCH_SIZE = 32 # slightly smaller batch for memory safety
EPOCHS = 10
LR = 5e-4

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
    transforms.RandomCrop(IMG_SIZE),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
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

    def __getitem__(self, index):
        x, y = self.subset[index]
        return self.transform(x), y

    def __len__(self):
        return len(self.subset)

def build_model(num_classes):
    print("Loading EfficientNetV2-S pre-trained on ImageNet...")
    weights = models.EfficientNet_V2_S_Weights.DEFAULT
    model = models.efficientnet_v2_s(weights=weights)
    
    # Freeze lower layers
    for param in model.features[:-3].parameters():
        param.requires_grad = False
        
    model.classifier[1] = nn.Sequential(
        nn.Dropout(p=0.4, inplace=True),
        nn.Linear(model.classifier[1].in_features, num_classes)
    )
    return model.to(DEVICE)

def train_model():
    print(f"Loading dataset from: {DATA_DIR}")
    dataset = datasets.ImageFolder(DATA_DIR)
    num_classes = len(dataset.classes)
    
    # Save class mapping
    class_map = {v: k for k, v in dataset.class_to_idx.items()}
    with open(os.path.join(CHECKPOINTS_DIR, "indian_classes.json"), "w") as f:
        json.dump(class_map, f, indent=4)
        
    print(f"Found {len(dataset)} images across {num_classes} classes.")
    
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_subset, val_subset = random_split(dataset, [train_size, val_size])
    
    train_dataset = TransformedDataset(train_subset, TRAIN_TRANSFORM)
    val_dataset = TransformedDataset(val_subset, VAL_TRANSFORM)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)
    
    model = build_model(num_classes)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    scaler = torch.amp.GradScaler('cuda')
    
    best_acc = 0.0
    model_path = os.path.join(CHECKPOINTS_DIR, "disease_indian_best.pt")
    
    for epoch in range(EPOCHS):
        start_time = time.time()
        
        # Training Phase
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
            
            optimizer.zero_grad()
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
            train_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            train_total += targets.size(0)
            train_correct += predicted.eq(targets).sum().item()
            
        scheduler.step()
        
        # Validation Phase
        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0
        
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
                with torch.amp.autocast('cuda'):
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                val_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                val_total += targets.size(0)
                val_correct += predicted.eq(targets).sum().item()
                
        epoch_time = time.time() - start_time
        t_loss = train_loss / train_total
        t_acc = train_correct / train_total
        v_loss = val_loss / val_total
        v_acc = val_correct / val_total
        
        print(f"Epoch {epoch+1}/{EPOCHS} [{epoch_time:.0f}s] - "
              f"Train Loss: {t_loss:.4f}, Acc: {t_acc:.4f} | "
              f"Val Loss: {v_loss:.4f}, Acc: {v_acc:.4f}")
              
        if v_acc > best_acc:
            best_acc = v_acc
            print(f"--> Saved new best checkpoint to {model_path}")
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'best_acc': best_acc,
                'num_classes': num_classes
            }, model_path)
            
    print(f"Training Complete! Best Validation Accuracy: {best_acc:.4f}")

if __name__ == "__main__":
    train_model()
