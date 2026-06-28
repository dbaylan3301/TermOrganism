"""ScalpBrain - Deep Neural Architecture for trading."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BrainOutput:
    """ScalpBrain output."""
    meta_prediction: torch.Tensor  # [batch, 3] - Buy/Sell/Hold probabilities
    actor_logits: torch.Tensor     # [batch, 3] - RL action logits
    critic_value: torch.Tensor     # [batch, 1] - State value
    attention_weights: Optional[torch.Tensor] = None
    uncertainty: Optional[torch.Tensor] = None


class ResidualBlock(nn.Module):
    """Residual connection block."""
    
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv1d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(channels)
        self.conv2 = nn.Conv1d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(channels)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return F.relu(out + residual)


class DilatedConvBlock(nn.Module):
    """Dilated convolution for wider receptive field."""
    
    def __init__(self, in_channels: int, out_channels: int, dilation: int = 1):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size=3, 
                              padding=dilation, dilation=dilation)
        self.bn = nn.BatchNorm1d(out_channels)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(self.bn(self.conv(x)))


class ScalpBrain(nn.Module):
    """
    ScalpBrain - Human Brain-Inspired Deep Neural Architecture.
    
    Components:
    - CNN Feature Extractor (Sensory Cortex)
    - Stacked LSTM (Hippocampus/Temporal Lobe)
    - Transformer Encoder (Association Areas)
    - Multi-Head Attention (Attention Mechanism)
    - Meta Output Head (Decision Making)
    - Actor-Critic Heads (RL/Prefrontal Cortex)
    """
    
    def __init__(
        self,
        input_dim: int = 64,
        hidden_dim: int = 512,
        num_lstm_layers: int = 4,
        num_transformer_layers: int = 6,
        num_heads: int = 8,
        dropout: float = 0.3,
        num_actions: int = 3
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # CNN Feature Extractor (Sensory Cortex)
        self.cnn = nn.Sequential(
            nn.Conv1d(input_dim, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            
            ResidualBlock(128),
            ResidualBlock(128),
            
            DilatedConvBlock(128, 256, dilation=2),
            ResidualBlock(256),
            
            DilatedConvBlock(256, 512, dilation=4),
            ResidualBlock(512),
            
            nn.Conv1d(512, hidden_dim, kernel_size=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )
        
        # Temporal Memory (Hippocampus)
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_lstm_layers,
            batch_first=True,
            dropout=dropout if num_lstm_layers > 1 else 0,
            bidirectional=True
        )
        
        # LSTM output projection (bidirectional -> hidden_dim)
        self.lstm_proj = nn.Linear(hidden_dim * 2, hidden_dim)
        
        # Transformer Encoder (Association Areas)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
            norm_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, 
            num_layers=num_transformer_layers
        )
        
        # Multi-Head Attention (Attention Mechanism)
        self.self_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        self.attention_norm = nn.LayerNorm(hidden_dim)
        
        # Meta Output Head (Decision Making)
        self.meta_head = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, 64),
            nn.GELU(),
            nn.Linear(64, num_actions)  # Buy, Sell, Hold
        )
        
        # Actor-Critic Heads (RL/Prefrontal Cortex)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, num_actions)
        )
        
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, 1)
        )
        
        # Uncertainty Estimation (Amygdala)
        self.uncertainty_head = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.GELU(),
            nn.Linear(128, num_actions),
            nn.Softmax(dim=-1)
        )
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights with Xavier/Kaiming."""
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> BrainOutput:
        """
        Forward pass.
        
        Args:
            x: [batch_size, seq_len, input_dim]
            
        Returns:
            BrainOutput with all predictions
        """
        batch_size, seq_len, _ = x.shape
        
        # CNN Feature Extraction (Sensory Cortex)
        cnn_input = x.transpose(1, 2)
        cnn_out = self.cnn(cnn_input)
        cnn_out = cnn_out.transpose(1, 2)
        
        # LSTM Temporal Memory (Hippocampus)
        lstm_out, (h_n, c_n) = self.lstm(cnn_out)
        lstm_out = self.lstm_proj(lstm_out)
        
        # Transformer Encoding (Association Areas)
        transformer_out = self.transformer(lstm_out)
        
        # Self-Attention (Attention Mechanism)
        attn_out, attn_weights = self.self_attention(
            transformer_out, transformer_out, transformer_out
        )
        attn_out = self.attention_norm(transformer_out + attn_out)
        
        # Get final hidden state
        final_hidden = attn_out[:, -1, :]  # [batch, hidden_dim]
        
        # Meta Prediction (Decision Making)
        meta_pred = self.meta_head(final_hidden)
        
        # Actor-Critic (RL)
        actor_logits = self.actor(final_hidden)
        critic_value = self.critic(final_hidden)
        
        # Uncertainty Estimation (Amygdala)
        uncertainty = self.uncertainty_head(final_hidden)
        
        return BrainOutput(
            meta_prediction=meta_pred,
            actor_logits=actor_logits,
            critic_value=critic_value,
            attention_weights=attn_weights,
            uncertainty=uncertainty
        )
    
    def get_action(self, state: torch.Tensor, temperature: float = 1.0) -> Tuple[int, float, float]:
        """
        Get action with temperature scaling for exploration.
        
        Returns:
            action, probability, value
        """
        with torch.no_grad():
            output = self.forward(state)
            
            # Temperature scaling
            logits = output.actor_logits / temperature
            probs = F.softmax(logits, dim=-1)
            
            # Sample action
            action = torch.multinomial(probs, 1).item()
            prob = probs[0, action].item()
            value = output.critic_value.item()
            
            return action, prob, value
    
    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
