---
inclusion: always
---

# ML Rules

## Primary Model
- Random Forest Classifier (scikit-learn)
- XGBoost may be added later as an optional comparison — it is NOT required for Phase 1
- Do NOT use TensorFlow, PyTorch, or any deep learning framework

## Classes
Three target classes:
- NORMAL
- CONGESTION
- FAILURE

RECOVERY may be added as a fourth class when sufficient data exists.

## Feature Set (initial)
Features derived from network monitoring:
- throughput_mbps
- delay_ms
- packet_loss_pct
- utilization_pct
- traffic_rate_mbps
- queue_length (if reliably available)
- link_status (binary: 1=up, 0=down)

Additional engineered features may be added after baseline validation.

## Pipeline Order
```
Raw CSV dataset
    │
Validation (schema check, range check, missing value check)
    │
Preprocessing (scaling, encoding, train/test split)
    │
Random Forest training
    │
Evaluation (accuracy, precision, recall, F1, confusion matrix)
    │
Model saved with joblib
    │
Prediction API (accepts feature dict, returns label + confidence)
```

## Data Rules
- The final training dataset must come from real Mininet experiments
- Synthetic/mock data may be used ONLY for:
  - Unit testing the pipeline on Windows
  - Verifying that preprocessing handles edge cases
  - Early algorithm development
- Synthetic data must be clearly labelled in filenames and comments:
  - Filename: synthetic_<description>.csv
  - Comment: # SYNTHETIC DATA — do not use for final model evaluation
- Never present synthetic results as real network performance

## Validation Requirements
- Minimum recommended dataset: 500+ samples across all classes
- Report class distribution before training
- If dataset is imbalanced (any class < 20% of total):
  - Report the imbalance explicitly
  - Consider stratified split
  - Do NOT claim reliable performance without addressing imbalance
- If dataset is too small (< 100 samples total):
  - Refuse to present accuracy as meaningful
  - Label results as "preliminary — insufficient data"

## Evaluation
- Use stratified train/test split (default 80/20)
- Report per-class precision, recall, and F1 (not just overall accuracy)
- Generate and save confusion matrix
- Use a fixed random_state seed for reproducibility (document the seed used)
- Do not tune hyperparameters to maximise accuracy on the test set without
  cross-validation

## Model Persistence
- Save trained models with joblib to ml/models/
- Filename format: rf_model_<timestamp>.joblib
- Also save a symlink or reference file: ml/models/current_model.txt
  containing the path to the active model
- ml/models/ directory is git-ignored (models are large binary files)
- Document model metadata alongside each saved model:
  - training date
  - dataset used
  - class distribution
  - hyperparameters
  - evaluation metrics

## Prediction API
The predict() function must:
- Accept a dictionary of feature values
- Validate that all required features are present
- Return both the predicted label and the confidence (probability)
- Never hard-code predictions
- Raise a clear error if the model file is missing

Example contract:
```python
def predict(features: dict) -> dict:
    """
    Returns:
        {
            "label": "CONGESTION",
            "confidence": 0.87,
            "probabilities": {"NORMAL": 0.08, "CONGESTION": 0.87, "FAILURE": 0.05}
        }
    """
```

## No Fabrication
- Never fabricate accuracy, F1, confusion matrix values, or improvement claims
- If a model has not been trained on real data, label all metrics as:
  "preliminary / synthetic-data-only — not representative of real network performance"
