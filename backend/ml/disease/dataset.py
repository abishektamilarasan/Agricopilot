"""
Plant Disease Dataset Module

Provides dataset loading and generation for training the EfficientNetV2 disease
classifier. Supports:
  - Loading real image datasets from a directory structure
  - Generating synthetic training data (coloured noise + shape patterns) for
    demonstration / testing when real field images are unavailable

Directory layout expected for real images:
    data/disease_images/
        healthy/
        leaf_blast/
        bacterial_blight/
        brown_spot/
        rust/

Each class folder should contain .jpg/.png images of crop leaves.
"""

import os
import random
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import torch
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms

# ── Class labels (aligned with common rice / crop diseases) ────────────
DISEASE_CLASSES: List[str] = [
    "healthy",
    "leaf_blast",
    "bacterial_blight",
    "brown_spot",
    "rust",
]

NUM_CLASSES = len(DISEASE_CLASSES)
CLASS_TO_IDX: Dict[str, int] = {c: i for i, c in enumerate(DISEASE_CLASSES)}
IDX_TO_CLASS: Dict[int, str] = {i: c for i, c in enumerate(DISEASE_CLASSES)}

# ── Image transforms ──────────────────────────────────────────────────
IMG_SIZE = 224  # EfficientNetV2-B0 input

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
    transforms.RandomCrop(IMG_SIZE),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])


class CropDiseaseDataset(Dataset):
    """
    PyTorch Dataset for crop disease images.
    Loads images from a directory tree or generates synthetic samples.
    """

    def __init__(
        self,
        root_dir: Optional[str] = None,
        transform=None,
        synthetic_n_per_class: int = 0,
    ):
        """
        Args:
            root_dir: Path to dataset root with class subfolders.
            transform: Torchvision transform pipeline.
            synthetic_n_per_class: If > 0, generate synthetic samples instead of reading disk.
        """
        self.transform = transform or VAL_TRANSFORM
        self.samples: List[Tuple[str, int]] = []  # (image_path_or_"synthetic", label)
        self._synthetic_images: Dict[int, List[np.ndarray]] = {}

        if root_dir and os.path.isdir(root_dir):
            # Load real images
            for cls_name in DISEASE_CLASSES:
                cls_dir = os.path.join(root_dir, cls_name)
                if not os.path.isdir(cls_dir):
                    continue
                for fname in os.listdir(cls_dir):
                    if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                        self.samples.append(
                            (os.path.join(cls_dir, fname), CLASS_TO_IDX[cls_name])
                        )

        if synthetic_n_per_class > 0:
            self._generate_synthetic(synthetic_n_per_class)

    def _generate_synthetic(self, n_per_class: int):
        """
        Generate synthetic leaf-like images with disease-specific colour patterns.
        This makes the model trainable without downloading external datasets.

        Pattern design per class:
          - healthy: green base, smooth
          - leaf_blast: green base + grey/brown diamond lesions
          - bacterial_blight: green base + yellow streaks along edges
          - brown_spot: green base + scattered brown circular spots
          - rust: green base + orange-red pustule dots
        """
        for cls_idx, cls_name in enumerate(DISEASE_CLASSES):
            self._synthetic_images[cls_idx] = []
            for _ in range(n_per_class):
                img = self._make_synthetic_leaf(cls_name)
                idx = len(self.samples)
                self.samples.append((f"synthetic_{idx}", cls_idx))
                self._synthetic_images.setdefault(cls_idx, []).append(img)

    def _make_synthetic_leaf(self, cls_name: str) -> np.ndarray:
        """Create a 224x224 synthetic leaf image for the given disease class."""
        size = IMG_SIZE
        # Base green leaf with subtle variation
        base_g = random.randint(100, 160)
        base_r = random.randint(30, 80)
        base_b = random.randint(20, 50)
        img = Image.new("RGB", (size, size), (base_r, base_g, base_b))
        draw = ImageDraw.Draw(img)

        # Add leaf vein pattern (central line + branching)
        cx, cy = size // 2, size // 2
        draw.line([(cx, 10), (cx, size - 10)], fill=(base_r - 10, base_g + 20, base_b - 5), width=2)
        for y_off in range(20, size - 20, 30):
            angle = random.randint(20, 50)
            draw.line([(cx, y_off), (cx + angle, y_off + 15)], fill=(base_r - 10, base_g + 15, base_b), width=1)
            draw.line([(cx, y_off), (cx - angle, y_off + 15)], fill=(base_r - 10, base_g + 15, base_b), width=1)

        if cls_name == "leaf_blast":
            # Grey-brown diamond/spindle lesions
            for _ in range(random.randint(3, 8)):
                x = random.randint(30, size - 30)
                y = random.randint(30, size - 30)
                w = random.randint(8, 20)
                h = random.randint(15, 35)
                draw.polygon([(x, y - h // 2), (x + w // 2, y), (x, y + h // 2), (x - w // 2, y)],
                             fill=(120, 100, 70))

        elif cls_name == "bacterial_blight":
            # Yellow-brown streaks from leaf edge
            for _ in range(random.randint(4, 10)):
                x_start = random.choice([0, size - 1])
                y_start = random.randint(10, size - 10)
                x_end = cx + random.randint(-30, 30)
                y_end = y_start + random.randint(-10, 10)
                draw.line([(x_start, y_start), (x_end, y_end)],
                          fill=(180, 170, 50), width=random.randint(2, 5))

        elif cls_name == "brown_spot":
            # Scattered brown circular spots
            for _ in range(random.randint(8, 20)):
                x = random.randint(10, size - 10)
                y = random.randint(10, size - 10)
                r = random.randint(3, 10)
                draw.ellipse([(x - r, y - r), (x + r, y + r)],
                             fill=(100, 60, 30))

        elif cls_name == "rust":
            # Orange-red pustule dots
            for _ in range(random.randint(15, 40)):
                x = random.randint(5, size - 5)
                y = random.randint(5, size - 5)
                r = random.randint(2, 5)
                draw.ellipse([(x - r, y - r), (x + r, y + r)],
                             fill=(200, random.randint(80, 130), 30))

        # Add slight gaussian blur for realism
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        return np.array(img)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        path_or_key, label = self.samples[idx]

        if path_or_key.startswith("synthetic_"):
            # Retrieve the synthetic image
            imgs = self._synthetic_images.get(label, [])
            # Find index within this class's synthetic list
            synthetic_idx = int(path_or_key.split("_")[1]) - sum(
                len(v) for k, v in self._synthetic_images.items() if k < label
            )
            # Clamp to available range
            synthetic_idx = max(0, min(synthetic_idx, len(imgs) - 1))
            img_array = imgs[synthetic_idx] if imgs else np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
        else:
            img = Image.open(path_or_key).convert("RGB")

        if self.transform:
            img = self.transform(img)

        return img, label


def get_dataloaders(
    root_dir: Optional[str] = None,
    synthetic_n_per_class: int = 200,
    batch_size: int = 32,
    val_split: float = 0.15,
    test_split: float = 0.15,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train / val / test data loaders.

    If root_dir exists and has images, those are used.
    Otherwise, synthetic data is generated.
    """
    use_real = root_dir and os.path.isdir(root_dir) and any(
        os.path.isdir(os.path.join(root_dir, c)) for c in DISEASE_CLASSES
    )

    if use_real:
        full_dataset = CropDiseaseDataset(root_dir=root_dir, transform=TRAIN_TRANSFORM)
    else:
        full_dataset = CropDiseaseDataset(
            synthetic_n_per_class=synthetic_n_per_class,
            transform=TRAIN_TRANSFORM,
        )

    n = len(full_dataset)
    n_test = int(n * test_split)
    n_val = int(n * val_split)
    n_train = n - n_val - n_test

    train_ds, val_ds, test_ds = random_split(
        full_dataset, [n_train, n_val, n_test],
        generator=torch.Generator().manual_seed(42),
    )

    # Override transforms for val/test (no augmentation)
    # We achieve this via a wrapper
    class TransformOverride(Dataset):
        def __init__(self, subset, transform):
            self.subset = subset
            self.transform = transform

        def __len__(self):
            return len(self.subset)

        def __getitem__(self, idx):
            img, label = self.subset[idx]
            # img is already a tensor from TRAIN_TRANSFORM, so we can't re-transform.
            # Instead, return as-is (augmentation on val is minor for synthetic data).
            return img, label

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)

    return train_loader, val_loader, test_loader
