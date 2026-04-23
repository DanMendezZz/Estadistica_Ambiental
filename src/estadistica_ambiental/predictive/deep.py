"""Modelos de Deep Learning: LSTM y GRU para series temporales ambientales.

Requiere: pip install estadistica-ambiental[deep]  (torch + lightning)
Si PyTorch no está disponible, el import falla gracefully con ImportError.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


def _check_torch():
    try:
        import torch
        return torch
    except ImportError:
        raise ImportError(
            "PyTorch es necesario para modelos deep learning.\n"
            "Instalar: pip install estadistica-ambiental[deep]"
        )


class _LSTMNet:
    """Red LSTM mínima implementada en PyTorch puro (sin Lightning)."""

    def __init__(self, input_size: int, hidden_size: int, n_layers: int, dropout: float):
        torch = _check_torch()
        import torch.nn as nn

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, n_layers,
                                    batch_first=True, dropout=dropout if n_layers > 1 else 0)
                self.fc = nn.Linear(hidden_size, 1)

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])

        self.net = Net()
        self.torch = torch
        self.nn = nn

    def train_loop(self, X: np.ndarray, y: np.ndarray, epochs: int, lr: float):
        torch = self.torch
        optimizer = torch.optim.Adam(self.net.parameters(), lr=lr)
        criterion = self.nn.MSELoss()
        X_t = torch.FloatTensor(X)
        y_t = torch.FloatTensor(y).unsqueeze(1)
        self.net.train()
        for _ in range(epochs):
            optimizer.zero_grad()
            loss = criterion(self.net(X_t), y_t)
            loss.backward()
            optimizer.step()

    def predict(self, X: np.ndarray) -> np.ndarray:
        torch = self.torch
        self.net.eval()
        with torch.no_grad():
            X_t = torch.FloatTensor(X)
            return self.net(X_t).squeeze().numpy()


class LSTMModel(BaseModel):
    """LSTM simple para pronóstico ambiental de series univariadas.

    Usa ventana deslizante (lookback) como features de entrada.
    Requiere: pip install torch  (o [deep]).
    """

    name = "LSTM"

    def __init__(
        self,
        lookback: int = 24,
        hidden_size: int = 64,
        n_layers: int = 2,
        dropout: float = 0.1,
        epochs: int = 50,
        lr: float = 1e-3,
    ):
        super().__init__(lookback=lookback, hidden_size=hidden_size,
                         n_layers=n_layers, epochs=epochs)
        self.lookback = lookback
        self.hidden_size = hidden_size
        self.n_layers = n_layers
        self.dropout = dropout
        self.epochs = epochs
        self.lr = lr
        self._net = None
        self._scaler_mean = 0.0
        self._scaler_std = 1.0
        self._history: Optional[np.ndarray] = None

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "LSTMModel":
        _check_torch()
        vals = y.dropna().values.astype(float)
        self._scaler_mean = vals.mean()
        self._scaler_std  = vals.std() if vals.std() > 0 else 1.0
        scaled = (vals - self._scaler_mean) / self._scaler_std

        X_win, y_win = self._make_windows(scaled)
        self._net = _LSTMNet(self.lookback, self.hidden_size, self.n_layers, self.dropout)
        self._net.train_loop(X_win, y_win, self.epochs, self.lr)
        self._history = scaled[-self.lookback:]
        self._fitted = True
        logger.info("LSTM ajustado: %d pasos de lookback, %d epochs", self.lookback, self.epochs)
        return self

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Llama fit() primero.")
        _check_torch()
        history = list(self._history)
        preds = []
        for _ in range(horizon):
            window = np.array(history[-self.lookback:]).reshape(1, self.lookback, 1)
            p = float(self._net.predict(window))
            preds.append(p)
            history.append(p)
        return np.array(preds) * self._scaler_std + self._scaler_mean

    def _make_windows(self, series: np.ndarray):
        X, y = [], []
        for i in range(len(series) - self.lookback):
            X.append(series[i:i + self.lookback].reshape(self.lookback, 1))
            y.append(series[i + self.lookback])
        return np.array(X), np.array(y)


class GRUModel(LSTMModel):
    """GRU — misma interfaz que LSTM, arquitectura más ligera."""

    name = "GRU"

    def _build_net(self):
        _check_torch()
        import torch.nn as nn

        class GRUNet(nn.Module):
            def __init__(self, lookback, hidden_size, n_layers, dropout):
                super().__init__()
                self.gru = nn.GRU(lookback, hidden_size, n_layers,
                                  batch_first=True, dropout=dropout if n_layers > 1 else 0)
                self.fc  = nn.Linear(hidden_size, 1)

            def forward(self, x):
                out, _ = self.gru(x)
                return self.fc(out[:, -1, :])

        return GRUNet(self.lookback, self.hidden_size, self.n_layers, self.dropout)
