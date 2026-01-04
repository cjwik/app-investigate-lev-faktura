import argparse
from unittest.mock import patch
import pytest
from src import main

@pytest.fixture
def mock_config():
    """Mock the config module imported in src.main."""
    with patch("src.main.config") as mock:
        yield mock

def test_cmd_setup_creates_directories(mock_config, tmp_path):
    """Verify setup command creates output directories when inputs exist."""
    # Arrange
    # Define paths using tmp_path
    mock_config.INPUT_DIR = tmp_path / "Input"
    mock_config.SIE_DIR = mock_config.INPUT_DIR / "SIE"
    mock_config.INPUT_VOUCHERS_2024 = mock_config.INPUT_DIR / "Verifikationer 2024"
    mock_config.INPUT_VOUCHERS_2025 = mock_config.INPUT_DIR / "Verifikationer 2025"
    
    # Create the input directories (simulating existing data)
    mock_config.SIE_DIR.mkdir(parents=True)
    mock_config.INPUT_VOUCHERS_2024.mkdir(parents=True)
    mock_config.INPUT_VOUCHERS_2025.mkdir(parents=True)

    # Define output directories (these should be created by setup)
    mock_config.OUTPUT_VOUCHERS_2024 = tmp_path / "Output" / "Vouchers" / "2024"
    mock_config.OUTPUT_VOUCHERS_2025 = tmp_path / "Output" / "Vouchers" / "2025"
    mock_config.REPORTS_DIR = tmp_path / "Output" / "reports"
    mock_config.LOGS_DIR = tmp_path / "logs"
    
    # Act
    args = argparse.Namespace(command="setup")
    result = main.cmd_setup(args)

    # Assert
    assert result == 0
    assert mock_config.OUTPUT_VOUCHERS_2024.exists()
    assert mock_config.OUTPUT_VOUCHERS_2025.exists()
    assert mock_config.REPORTS_DIR.exists()
    assert mock_config.LOGS_DIR.exists()

def test_cmd_setup_fails_missing_input(mock_config, tmp_path):
    """Verify setup command fails if input directories are missing."""
    # Arrange
    # Point to non-existent paths
    mock_config.INPUT_DIR = tmp_path / "MissingInput"
    mock_config.SIE_DIR = mock_config.INPUT_DIR / "SIE"
    mock_config.INPUT_VOUCHERS_2024 = mock_config.INPUT_DIR / "Verifikationer 2024"
    mock_config.INPUT_VOUCHERS_2025 = mock_config.INPUT_DIR / "Verifikationer 2025"
    
    # Act
    args = argparse.Namespace(command="setup")
    result = main.cmd_setup(args)

    # Assert
    assert result == 2