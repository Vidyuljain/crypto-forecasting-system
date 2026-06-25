"""
models.py — Train machine learning models for cryptocurrency price forecasting.

Uses scikit-learn to build and train simple regression models.
"""

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


def train_linear_model(X, y):
    """
    Train a simple Linear Regression model.

    Linear Regression finds a straight-line relationship between features
    (previous_price, 7_day_average) and the future price.

    Good for: quick baseline, easy to understand.
    Fast to train on small datasets.
    """
    model = LinearRegression()
    model.fit(X, y)
    return model


def train_random_forest(X, y):
    """
    Train a Random Forest Regressor model.

    Random Forest builds many decision trees and averages their predictions.
    It can capture more complex patterns than a single straight line.

    Good for: better accuracy on non-linear price patterns.
    """
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model
