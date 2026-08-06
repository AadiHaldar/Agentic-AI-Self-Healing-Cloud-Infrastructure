import os
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ResourceLSTM(nn.Module):
    """
    Lightweight LSTM model for predicting future resource utilization
    based on historical time-series data.
    """
    def __init__(self, input_size=1, hidden_layer_size=50, output_size=1):
        super(ResourceLSTM, self).__init__()
        self.hidden_layer_size = hidden_layer_size
        self.lstm = nn.LSTM(input_size, hidden_layer_size, batch_first=True)
        self.linear = nn.Linear(hidden_layer_size, output_size)

    def forward(self, input_seq):
        lstm_out, _ = self.lstm(input_seq)
        predictions = self.linear(lstm_out[:, -1, :])
        return predictions

class PredictiveForecaster:
    """
    Wrapper for training and predicting with the ResourceLSTM model.
    Auto-trains on `datasets/healthy_telemetry.csv` if available.
    """
    def __init__(self, model_path: str = None):
        self.model = ResourceLSTM()
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.005)
        
        # Load dataset and train baseline if dataset exists
        dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../datasets/healthy_telemetry.csv"))
        if os.path.exists(dataset_path):
            try:
                df = pd.read_csv(dataset_path)
                cpu_series = df["cpu_usage"].values
                self._fit_baseline(cpu_series)
            except Exception as e:
                logger.warning(f"Could not train LSTM on dataset: {e}")

    def _fit_baseline(self, series: np.ndarray, seq_len: int = 10, epochs: int = 15):
        """Build sliding window sequences and train PyTorch LSTM."""
        X, y = [], []
        for i in range(len(series) - seq_len):
            X.append(series[i:i+seq_len])
            y.append(series[i+seq_len])
            
        X = np.array(X, dtype=np.float32).reshape(-1, seq_len, 1)
        y = np.array(y, dtype=np.float32).reshape(-1, 1)

        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)

        self.model.train()
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            y_pred = self.model(X_tensor)
            loss = self.criterion(y_pred, y_tensor)
            loss.backward()
            self.optimizer.step()
            
        logger.info(f"[PredictiveForecaster] PyTorch LSTM baseline trained. Loss: {loss.item():.5f}")

    def predict_future(self, current_sequence: np.ndarray) -> float:
        """
        Predict the next time-step value based on the input sequence.
        Handles 1D, 2D, and 3D input tensor shapes correctly.
        """
        self.model.eval()
        with torch.no_grad():
            seq_arr = np.array(current_sequence, dtype=np.float32)
            if seq_arr.ndim == 1:
                seq_arr = seq_arr.reshape(1, -1, 1)
            elif seq_arr.ndim == 2:
                seq_arr = np.expand_dims(seq_arr, axis=-1) if seq_arr.shape[0] == 1 else np.expand_dims(seq_arr, axis=0)
                
            seq_tensor = torch.FloatTensor(seq_arr)
            prediction = self.model(seq_tensor)
            return float(prediction.item())
