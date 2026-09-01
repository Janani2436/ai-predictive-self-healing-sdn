"""
ml package
WINDOWS-COMPATIBLE

Machine learning pipeline for network condition classification.
No Linux networking dependencies — fully testable on the Windows
development machine.

Modules:
    preprocess  — validation, cleaning, feature scaling, stratified split
    train       — Random Forest training with configurable hyperparameters
    evaluate    — accuracy, precision, recall, F1, confusion matrix
    predict     — inference API: accepts feature dict, returns label + confidence
"""
