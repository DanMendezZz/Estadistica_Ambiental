"""Modelos de Deep Learning: LSTM, BiLSTM y GRU para series temporales ambientales.

Requiere: pip install estadistica-ambiental[deep]  (torch + lightning)
Si PyTorch no está disponible, el import falla gracefully con ImportError.

Todas las clases implementan el contrato :class:`BaseModel` y, además, exponen
los miembros del protocolo :class:`ModelSpec` (``warm_starts``, ``suggest_params``,
``build_model``, ``search_space``) para integrarse en el pipeline de
optimización bayesiana y en :func:`estadistica_ambiental.evaluation.backtesting.walk_forward`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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


class _RecurrentNet:
    """Red recurrente mínima en PyTorch puro.

    Soporta LSTM (uni o bidireccional) y GRU según ``cell``.
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        n_layers: int,
        dropout: float,
        cell: str = "lstm",
        bidirectional: bool = False,
    ):
        torch = _check_torch()
        import torch.nn as nn

        cell_lower = cell.lower()
        if cell_lower not in {"lstm", "gru"}:
            raise ValueError(f"cell debe ser 'lstm' o 'gru', recibido '{cell}'")

        rnn_cls = nn.LSTM if cell_lower == "lstm" else nn.GRU
        out_factor = 2 if bidirectional else 1

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.rnn = rnn_cls(
                    input_size,
                    hidden_size,
                    n_layers,
                    batch_first=True,
                    dropout=dropout if n_layers > 1 else 0,
                    bidirectional=bidirectional,
                )
                self.fc = nn.Linear(hidden_size * out_factor, 1)

            def forward(self, x):
                out, _ = self.rnn(x)
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
    """LSTM para pronóstico ambiental univariado con ventana deslizante.

    Implementa :class:`BaseModel` (``fit``/``predict``/``is_fitted``) y el
    protocolo :class:`ModelSpec` (``warm_starts``/``suggest_params``/
    ``build_model``/``search_space``) para uso directo con
    :func:`walk_forward` y el optimizador bayesiano.

    Requiere: pip install torch  (o el extra ``[deep]``).
    """

    name = "LSTM"
    _cell: str = "lstm"
    _bidirectional: bool = False

    def __init__(
        self,
        lookback: int = 24,
        hidden_size: int = 64,
        n_layers: int = 2,
        dropout: float = 0.1,
        epochs: int = 50,
        lr: float = 1e-3,
    ):
        super().__init__(
            lookback=lookback,
            hidden_size=hidden_size,
            n_layers=n_layers,
            dropout=dropout,
            epochs=epochs,
            lr=lr,
        )
        self.lookback = lookback
        self.hidden_size = hidden_size
        self.n_layers = n_layers
        self.dropout = dropout
        self.epochs = epochs
        self.lr = lr
        self._net: Optional[_RecurrentNet] = None
        self._scaler_mean = 0.0
        self._scaler_std = 1.0
        self._history: Optional[np.ndarray] = None
        self._loss: Optional[float] = None

    # ------------------------------------------------------------------ BaseModel

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "LSTMModel":
        _check_torch()
        vals = np.asarray(y.dropna().values, dtype=float)
        if len(vals) <= self.lookback:
            raise ValueError(
                f"La serie ({len(vals)} obs) debe tener más puntos que "
                f"lookback ({self.lookback})."
            )
        self._scaler_mean = float(vals.mean())
        self._scaler_std = float(vals.std()) if vals.std() > 0 else 1.0
        scaled = (vals - self._scaler_mean) / self._scaler_std

        X_win, y_win = self._make_windows(scaled)
        self._net = _RecurrentNet(
            input_size=1,
            hidden_size=self.hidden_size,
            n_layers=self.n_layers,
            dropout=self.dropout,
            cell=self._cell,
            bidirectional=self._bidirectional,
        )
        self._net.train_loop(X_win, y_win, self.epochs, self.lr)
        self._history = scaled[-self.lookback :]
        self._fitted = True
        logger.info(
            "%s ajustado: %d pasos de lookback, %d epochs", self.name, self.lookback, self.epochs
        )
        return self

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Llama fit() primero.")
        _check_torch()
        history = list(self._history)
        preds = []
        for _ in range(horizon):
            window = np.array(history[-self.lookback :]).reshape(1, self.lookback, 1)
            p = float(self._net.predict(window))
            preds.append(p)
            history.append(p)
        return np.array(preds) * self._scaler_std + self._scaler_mean

    def _make_windows(self, series: np.ndarray):
        X, y = [], []
        for i in range(len(series) - self.lookback):
            X.append(series[i : i + self.lookback].reshape(self.lookback, 1))
            y.append(series[i + self.lookback])
        return np.array(X), np.array(y)

    # ------------------------------------------------------------------ summary

    def summary(self) -> Dict[str, Any]:
        """Resumen rápido del modelo (compatible con clásicos)."""
        return {
            "name": self.name,
            "fitted": self._fitted,
            "lookback": self.lookback,
            "hidden_size": self.hidden_size,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
            "epochs": self.epochs,
            "lr": self.lr,
            "bidirectional": self._bidirectional,
            "cell": self._cell,
        }

    # ------------------------------------------------------------------ ModelSpec

    @property
    def warm_starts(self) -> List[Dict[str, Any]]:
        return [
            {"lookback": 24, "hidden_size": 64, "n_layers": 2, "dropout": 0.1, "lr": 1e-3},
            {"lookback": 48, "hidden_size": 128, "n_layers": 2, "dropout": 0.2, "lr": 5e-4},
        ]

    def suggest_params(self, trial: Any) -> Dict[str, Any]:
        return {
            "lookback": trial.suggest_int("lookback", 6, 96),
            "hidden_size": trial.suggest_categorical("hidden_size", [16, 32, 64, 128]),
            "n_layers": trial.suggest_int("n_layers", 1, 3),
            "dropout": trial.suggest_float("dropout", 0.0, 0.5),
            "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
        }

    def build_model(self, params: Dict[str, Any]) -> "LSTMModel":
        return type(self)(
            lookback=params.get("lookback", self.lookback),
            hidden_size=params.get("hidden_size", self.hidden_size),
            n_layers=params.get("n_layers", self.n_layers),
            dropout=params.get("dropout", self.dropout),
            epochs=params.get("epochs", self.epochs),
            lr=params.get("lr", self.lr),
        )

    @property
    def search_space(self) -> Dict[str, Any]:
        return {
            "lookback": ("int", 6, 96),
            "hidden_size": ("categorical", [16, 32, 64, 128]),
            "n_layers": ("int", 1, 3),
            "dropout": ("float", 0.0, 0.5),
            "lr": ("loguniform", 1e-4, 1e-2),
        }


class BiLSTMModel(LSTMModel):
    """LSTM bidireccional. Misma interfaz que :class:`LSTMModel`."""

    name = "BiLSTM"
    _cell = "lstm"
    _bidirectional = True


class GRUModel(LSTMModel):
    """GRU — misma interfaz que LSTM, arquitectura más ligera."""

    name = "GRU"
    _cell = "gru"
    _bidirectional = False
