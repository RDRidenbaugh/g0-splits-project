"""ResNet18 backbone + deconvolutional heatmap head (simple-baseline style
pose estimation architecture). One model instance per view (Bottom/Left/
Right) since each has a different, fixed keypoint count.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torchvision


class HeatmapNet(nn.Module):
    def __init__(self, num_keypoints: int, pretrained: bool = True):
        super().__init__()
        weights = torchvision.models.ResNet18_Weights.DEFAULT if pretrained else None
        backbone = torchvision.models.resnet18(weights=weights)
        # keep everything up to (and including) layer4: stride 32, 512 channels
        self.backbone = nn.Sequential(
            backbone.conv1,
            backbone.bn1,
            backbone.relu,
            backbone.maxpool,
            backbone.layer1,
            backbone.layer2,
            backbone.layer3,
            backbone.layer4,
        )
        # 3x (deconv x2 + BN + ReLU): stride 32 -> stride 4 overall
        channels = [512, 256, 256, 256]
        deconv_layers = []
        for in_c, out_c in zip(channels[:-1], channels[1:]):
            deconv_layers += [
                nn.ConvTranspose2d(in_c, out_c, kernel_size=4, stride=2, padding=1, bias=False),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            ]
        self.deconv = nn.Sequential(*deconv_layers)
        self.head = nn.Conv2d(channels[-1], num_keypoints, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        feat = self.deconv(feat)
        return self.head(feat)
