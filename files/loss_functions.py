import torch
import torch.nn as nn
import torch.nn.functional as F

####################
# Loss functions
####################
# code taken from: https://www.kaggle.com/bigironsphere/loss-function-library-keras-pytorch

# Dice Loss
class DiceLoss(nn.Module):
    def __init__(self, weight=None, size_average=True):
        super(DiceLoss, self).__init__()

    def forward(self, inputs, targets, smooth=1):
        # use torch.sigmoid instead of F.sigmoid
        inputs = torch.sigmoid(inputs)

        # flatten label and prediction tensors
        inputs = inputs.view(-1)
        targets = targets.view(-1)

        intersection = (inputs * targets).sum()
        dice = (2. * intersection + smooth) / (inputs.sum() + targets.sum() + smooth)

        return 1 - dice

# Dice BCE Loss
class DiceBCELoss(nn.Module):
    def __init__(self, weight=None, size_average=True):
        super(DiceBCELoss, self).__init__()

    def forward(self, inputs, targets, smooth=1):
        # comment out if your model contains a sigmoid or equivalent activation layer
        inputs = torch.sigmoid(inputs)

        # flatten label and prediction tensors
        inputs = inputs.view(-1)
        targets = targets.view(-1)

        intersection = (inputs * targets).sum()
        dice_loss = 1 - (2. * intersection + smooth) / (inputs.sum() + targets.sum() + smooth)
        BCE = F.binary_cross_entropy(inputs, targets, reduction='mean')
        Dice_BCE = BCE + dice_loss

        return Dice_BCE

# IoU Loss
class IoULoss(nn.Module):
    def __init__(self, weight=None, size_average=True):
        super(IoULoss, self).__init__()

    def forward(self, inputs, targets, smooth=1):
        # comment out if your model contains a sigmoid or equivalent activation layer
        inputs = torch.sigmoid(inputs)

        # flatten label and prediction tensors
        inputs = inputs.view(-1)
        targets = targets.view(-1)

        # intersection is equivalent to True Positive count
        # union is the mutually inclusive area of all labels & predictions
        intersection = (inputs * targets).sum()
        total = (inputs + targets).sum()
        union = total - intersection

        IoU = (intersection + smooth) / (union + smooth)

        return 1 - IoU

# Focal Loss
ALPHA = 0.995
GAMMA = 2

class FocalLoss(nn.Module):
    """
    Focal Loss, as described in https://arxiv.org/abs/1708.02002.

    Binary Cross-Entropy (BCE):
    BCE is a loss function used to measure the difference between predicted probabilities and true binary labels (0 or 1)
    for each pixel. The BCE loss is low when the predicted probability is close to the ground truth label and high
    when it's far from the ground truth label. Mathematically, the BCE loss is defined as:
        BCE = -(y * log(p) + (1 - y) * log(1 - p)); where y is the ground truth label (0 or 1), and p is the predicted probability.
    Intuition: BCE penalizes wrong predictions more heavily when the model is more confident in them.
    For example, if the ground truth label is 1, and the model predicts a probability of 0.9, the BCE loss will be lower than if the model predicts a probability of 0.1.

    (1 - BCE_EXP):
    Intuition: is close to 0 for easy-to-classify pixels and close to 1 for hard-to-classify pixels.
    This term helps adjust the contribution of hard and easy pixels to the overall loss,
    allowing Focal Loss to focus on the hard-to-classify pixels during training, which is particularly helpful for imbalanced datasets.

    Hyperparameters a & y:
    α (alpha): This is a parameter that helps balance the importance of foreground and background classes in the
    loss calculation. If you want to put more emphasis on the foreground class, choose an alpha value closer to 1.
    If you want to give equal importance to both classes, choose an alpha value of 0.5.

    γ (gamma): This is a parameter that controls how much the model focuses on the hard-to-classify pixels.
    Higher gamma values make the model focus more on hard-to-classify pixels,
    while lower gamma values treat all pixels more equally.
    """
    def __init__(self, weight=None, size_average=True):
        super(FocalLoss, self).__init__()

    def forward(self, inputs, targets, alpha=ALPHA, gamma=GAMMA, smooth=1):
        # comment out if your model contains a sigmoid or equivalent activation layer
        inputs = torch.sigmoid(inputs)

        # flatten label and prediction tensors
        inputs = inputs.view(-1)
        targets = targets.view(-1)

        # first compute binary cross-entropy
        BCE = F.binary_cross_entropy(inputs, targets, reduction='mean')
        BCE_EXP = torch.exp(-BCE)
        focal_loss = alpha * (1 - BCE_EXP) ** gamma * BCE

        return focal_loss

# Tversky Loss
ALPHA = 0.5
BETA = 0.5

class TverskyLoss(nn.Module):
    """
    The Tversky loss takes two parameters, alpha and beta,
    which control the balance between false positives (FP) and false negatives (FN).
    When alpha = beta = 0.5, the Tversky loss becomes the Dice loss,
    and when alpha = beta = 1, it becomes the Jaccard loss.

    The Tversky loss can have a value between 0 and 1+,
    where 0 indicates a perfect match between the predicted segmentation and the ground truth,
    and 1 indicates no overlap.
    Depending on the values of alpha, beta, and smooth, the Tversky loss can also have values greater than 1,
    as there is no strict upper bound for the loss.
    """
    def __init__(self, weight=None, size_average=True):
        super(TverskyLoss, self).__init__()

    def forward(self, inputs, targets, smooth=1, alpha=ALPHA, beta=BETA):
        # comment out if your model contains a sigmoid or equivalent activation layer
        inputs = torch.sigmoid(inputs)

        # flatten label and prediction tensors
        inputs = inputs.view(-1)
        targets = targets.view(-1)

        # True Positives, False Positives & False Negatives
        TP = (inputs * targets).sum()
        FP = ((1 - targets) * inputs).sum()
        FN = (targets * (1 - inputs)).sum()

        Tversky = (TP + smooth) / (TP + alpha * FP + beta * FN + smooth)

        return 1 - Tversky