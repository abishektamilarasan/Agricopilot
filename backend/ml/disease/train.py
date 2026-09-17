"""
Disease Detection Training Pipeline

Trains EfficientNetV2-B0 on synthetic or real crop disease images with:
  - Two-phase training (frozen backbone → fine-tune last 3 blocks)
  - Mixed precision (AMP) on CUDA
  - Early stopping with patience
  - Learning rate scheduling (CosineAnnealingWarmRestarts)
  - Checkpoint saving (best val accuracy)
  - Metrics logging to JSON

Usage:
    python -m ml.disease.train
"""

import json
import os
import time
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader

from ml import DEVICE, CHECKPOINTS_DIR, REPORTS_DIR
from ml.disease.dataset import get_dataloaders, DISEASE_CLASSES
from ml.disease.model import create_model


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    scaler: Optional[GradScaler] = None,
) -> Dict[str, float]:
    """Train for one epoch. Returns dict with loss and accuracy."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        if scaler and device.type == "cuda":
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                outputs = model(images)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

        total_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += labels.size(0)

    return {
        "loss": total_loss / max(total, 1),
        "accuracy": correct / max(total, 1),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluate model on a data loader. Returns dict with loss, accuracy, per-class accuracy."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    class_correct = [0] * len(DISEASE_CLASSES)
    class_total = [0] * len(DISEASE_CLASSES)

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        outputs = model(images)
        loss = criterion(outputs, labels)

        total_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += labels.size(0)

        for i in range(labels.size(0)):
            label = labels[i].item()
            class_correct[label] += (predicted[i] == label).item()
            class_total[label] += 1

    per_class = {}
    for i, cls in enumerate(DISEASE_CLASSES):
        per_class[cls] = class_correct[i] / max(class_total[i], 1)

    return {
        "loss": total_loss / max(total, 1),
        "accuracy": correct / max(total, 1),
        "per_class_accuracy": per_class,
    }


def train_disease_model(
    data_dir: Optional[str] = None,
    synthetic_n_per_class: int = 200,
    phase1_epochs: int = 10,
    phase2_epochs: int = 15,
    batch_size: int = 32,
    lr_phase1: float = 1e-3,
    lr_phase2: float = 1e-4,
    patience: int = 5,
    device: torch.device = None,
) -> Dict:
    """
    Two-phase training:
      Phase 1: Train classifier head only (backbone frozen)
      Phase 2: Fine-tune last 3 backbone blocks + classifier

    Returns:
        Dictionary with training history and final metrics.
    """
    device = device or DEVICE
    print(f"[Disease Training] Device: {device}")
    print(f"[Disease Training] Synthetic samples/class: {synthetic_n_per_class}")

    # ── Data ──────────────────────────────────────────────────
    train_loader, val_loader, test_loader = get_dataloaders(
        root_dir=data_dir,
        synthetic_n_per_class=synthetic_n_per_class,
        batch_size=batch_size,
    )
    print(f"[Disease Training] Train: {len(train_loader.dataset)}, Val: {len(val_loader.dataset)}, Test: {len(test_loader.dataset)}")

    # ── Model ─────────────────────────────────────────────────
    model = create_model(pretrained=True, freeze_backbone=True, device=device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler = torch.amp.GradScaler("cuda") if device.type == "cuda" else None

    history = {"phase1": [], "phase2": [], "test": {}}
    best_val_acc = 0.0
    checkpoint_path = os.path.join(CHECKPOINTS_DIR, "disease_best.pt")

    # ── Phase 1: Train head only ──────────────────────────────
    print("\n═══ Phase 1: Training classifier head (backbone frozen) ═══")
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr_phase1, weight_decay=0.01,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=5, T_mult=1)
    no_improve = 0

    for epoch in range(1, phase1_epochs + 1):
        t0 = time.time()
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, scaler)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        record = {
            "epoch": epoch,
            "train_loss": round(train_metrics["loss"], 4),
            "train_acc": round(train_metrics["accuracy"], 4),
            "val_loss": round(val_metrics["loss"], 4),
            "val_acc": round(val_metrics["accuracy"], 4),
            "lr": optimizer.param_groups[0]["lr"],
            "time_s": round(elapsed, 1),
        }
        history["phase1"].append(record)
        print(f"  Epoch {epoch:2d}/{phase1_epochs} | "
              f"Train Loss: {record['train_loss']:.4f} Acc: {record['train_acc']:.4f} | "
              f"Val Loss: {record['val_loss']:.4f} Acc: {record['val_acc']:.4f} | "
              f"{record['time_s']:.1f}s")

        if val_metrics["accuracy"] > best_val_acc:
            best_val_acc = val_metrics["accuracy"]
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_accuracy": best_val_acc,
                "epoch": epoch,
                "phase": 1,
                "classes": DISEASE_CLASSES,
            }, checkpoint_path)
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"  Early stopping at epoch {epoch} (no improvement for {patience} epochs)")
                break

    # ── Phase 2: Fine-tune backbone ───────────────────────────
    print("\n═══ Phase 2: Fine-tuning last 3 backbone blocks ═══")
    model.unfreeze_backbone(unfreeze_from=-3)
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr_phase2, weight_decay=0.01,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=5, T_mult=1)
    no_improve = 0

    for epoch in range(1, phase2_epochs + 1):
        t0 = time.time()
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, scaler)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        record = {
            "epoch": epoch,
            "train_loss": round(train_metrics["loss"], 4),
            "train_acc": round(train_metrics["accuracy"], 4),
            "val_loss": round(val_metrics["loss"], 4),
            "val_acc": round(val_metrics["accuracy"], 4),
            "lr": optimizer.param_groups[0]["lr"],
            "time_s": round(elapsed, 1),
        }
        history["phase2"].append(record)
        print(f"  Epoch {epoch:2d}/{phase2_epochs} | "
              f"Train Loss: {record['train_loss']:.4f} Acc: {record['train_acc']:.4f} | "
              f"Val Loss: {record['val_loss']:.4f} Acc: {record['val_acc']:.4f} | "
              f"{record['time_s']:.1f}s")

        if val_metrics["accuracy"] > best_val_acc:
            best_val_acc = val_metrics["accuracy"]
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_accuracy": best_val_acc,
                "epoch": epoch,
                "phase": 2,
                "classes": DISEASE_CLASSES,
            }, checkpoint_path)
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"  Early stopping at epoch {epoch}")
                break

    # ── Test evaluation ───────────────────────────────────────
    print("\n═══ Final Test Evaluation ═══")
    # Load best checkpoint
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    test_metrics = evaluate(model, test_loader, criterion, device)
    history["test"] = {
        "loss": round(test_metrics["loss"], 4),
        "accuracy": round(test_metrics["accuracy"], 4),
        "per_class_accuracy": {k: round(v, 4) for k, v in test_metrics["per_class_accuracy"].items()},
        "best_val_accuracy": round(best_val_acc, 4),
    }
    print(f"  Test Accuracy: {history['test']['accuracy']:.4f}")
    print(f"  Per-class: {history['test']['per_class_accuracy']}")

    # ── Save metrics report ───────────────────────────────────
    report_path = os.path.join(REPORTS_DIR, "disease_metrics.json")
    with open(report_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"\n[Disease Training] Metrics saved to {report_path}")
    print(f"[Disease Training] Best checkpoint saved to {checkpoint_path}")

    return history


if __name__ == "__main__":
    train_disease_model()
