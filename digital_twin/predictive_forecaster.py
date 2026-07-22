import torch
import torch.nn as nn
import numpy as np
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

        # LSTM layer
        self.lstm = nn.LSTM(input_size, hidden_layer_size, batch_first=True)
        # Linear layer for output
        self.linear = nn.Linear(hidden_layer_size, output_size)

    def forward(self, input_seq):
        lstm_out, _ = self.lstm(input_seq)
        # We only want the last output of the sequence
        predictions = self.linear(lstm_out[:, -1, :])
        return predictions

class PredictiveForecaster:
    """
    Wrapper for training and predicting with the ResourceLSTM model.
    """
    def __init__(self, model_path: str = None):
        self.model = ResourceLSTM()
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        if model_path:
            try:
                self.model.load_state_dict(torch.load(model_path))
                self.model.eval()
            except Exception as e:
                logger.error(f"Failed to load model from {model_path}: {e}")

    def train(self, data: np.ndarray, epochs: int = 10):
        """
        Train the LSTM on historical data.
        `data` should be shape (batch_size, sequence_length, input_size)
        Target is assumed to be the next step (which we'd shift externally).
        For this MVP, this is a placeholder training loop.
        """
        self.model.train()
        # Mock training loop assuming `data` is (X, y)
        X, y = data
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)

        for i in range(epochs):
            self.optimizer.zero_grad()
            y_pred = self.model(X_tensor)
            single_loss = self.criterion(y_pred, y_tensor)
            single_loss.backward()
            self.optimizer.step()

        logger.info(f"Training complete. Final loss: {single_loss.item():.4f}")

    def predict_future(self, current_sequence: np.ndarray) -> float:
        """
        Predict the next value based on the current sequence of data.
        """
        self.model.eval()
        with torch.no_grad():
            seq_tensor = torch.FloatTensor(current_sequence).unsqueeze(0)  # Add batch dimension
            prediction = self.model(seq_tensor)
            return prediction.item()
