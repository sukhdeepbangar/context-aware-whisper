"""
Model Manager Module
Utility for downloading and managing whisper.cpp models.

Usage:
    python -m context_aware_whisper.model_manager list              # List available models
    python -m context_aware_whisper.model_manager download base.en  # Download a specific model
    python -m context_aware_whisper.model_manager info base.en      # Show model info
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from context_aware_whisper.local_transcriber import LocalTranscriber


# Model sizes (approximate, in bytes)
MODEL_SIZES = {
    "tiny": 75_000_000,
    "tiny.en": 75_000_000,
    "base": 142_000_000,
    "base.en": 142_000_000,
    "small": 466_000_000,
    "small.en": 466_000_000,
    "medium": 1_500_000_000,
    "medium.en": 1_500_000_000,
    "large-v1": 3_000_000_000,
    "large-v2": 3_000_000_000,
    "large-v3": 3_000_000_000,
}

# Model descriptions
MODEL_DESCRIPTIONS = {
    "tiny": "Fastest, basic quality",
    "tiny.en": "Fastest, English-only",
    "base": "Fast, good quality",
    "base.en": "Fast, English-only (recommended)",
    "small": "Medium speed, better quality",
    "small.en": "Medium speed, English-only",
    "medium": "Slow, great quality",
    "medium.en": "Slow, English-only",
    "large-v1": "Slowest, best quality (v1)",
    "large-v2": "Slowest, best quality (v2)",
    "large-v3": "Slowest, best quality (v3)",
}


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    elif size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.0f} MB"
    else:
        return f"{size_bytes / 1_000:.0f} KB"


def get_default_models_dir() -> Path:
    """Get the default models directory."""
    return Path.home() / ".cache" / "whisper"


def list_models(models_dir: Optional[str] = None) -> None:
    """
    List available whisper.cpp models and their download status.

    Args:
        models_dir: Optional custom models directory
    """
    models_path = Path(models_dir) if models_dir else get_default_models_dir()

    print("Available whisper.cpp models:")
    print("-" * 65)
    print(f"{'Model':<12} {'Size':<10} {'Status':<18} {'Description'}")
    print("-" * 65)

    for model in LocalTranscriber.AVAILABLE_MODELS:
        model_file = models_path / f"ggml-{model}.bin"
        size = format_size(MODEL_SIZES.get(model, 0))
        description = MODEL_DESCRIPTIONS.get(model, "")

        if model_file.exists():
            actual_size = model_file.stat().st_size
            status = f"Downloaded ({format_size(actual_size)})"
        else:
            status = "Not downloaded"

        print(f"{model:<12} {size:<10} {status:<18} {description}")

    print("-" * 65)
    print(f"\nModels directory: {models_path}")


def download_model(
    model_name: str,
    models_dir: Optional[str] = None,
    force: bool = False
) -> bool:
    """
    Download a specific whisper model.

    Args:
        model_name: Name of the model to download
        models_dir: Optional custom models directory
        force: Force re-download even if model exists

    Returns:
        True if download succeeded, False otherwise
    """
    if model_name not in LocalTranscriber.AVAILABLE_MODELS:
        print(f"Error: Unknown model '{model_name}'")
        print(f"Available models: {', '.join(LocalTranscriber.AVAILABLE_MODELS)}")
        return False

    try:
        transcriber = LocalTranscriber(
            model_name=model_name,
            models_dir=models_dir
        )

        if transcriber.is_model_downloaded() and not force:
            print(f"Model '{model_name}' is already downloaded.")
            print(f"Location: {transcriber.get_model_path()}")
            print("\nUse --force to re-download.")
            return True

        size = format_size(MODEL_SIZES.get(model_name, 0))
        print(f"Downloading model: {model_name} ({size})")
        print("This may take a few minutes depending on your connection...")
        print()

        # Trigger download by loading the model
        transcriber.download_model(show_progress=True)

        print()
        print(f"Model '{model_name}' downloaded successfully!")
        print(f"Location: {transcriber.get_model_path()}")
        return True

    except Exception as e:
        print(f"Error downloading model: {e}")
        return False


def show_model_info(model_name: str, models_dir: Optional[str] = None) -> None:
    """
    Show detailed information about a model.

    Args:
        model_name: Name of the model
        models_dir: Optional custom models directory
    """
    if model_name not in LocalTranscriber.AVAILABLE_MODELS:
        print(f"Error: Unknown model '{model_name}'")
        print(f"Available models: {', '.join(LocalTranscriber.AVAILABLE_MODELS)}")
        return

    models_path = Path(models_dir) if models_dir else get_default_models_dir()
    model_file = models_path / f"ggml-{model_name}.bin"

    print(f"Model: {model_name}")
    print("-" * 40)
    print(f"Description: {MODEL_DESCRIPTIONS.get(model_name, 'N/A')}")
    print(f"Expected size: {format_size(MODEL_SIZES.get(model_name, 0))}")
    print(f"File path: {model_file}")

    if model_file.exists():
        actual_size = model_file.stat().st_size
        print(f"Status: Downloaded")
        print(f"Actual size: {format_size(actual_size)}")
    else:
        print(f"Status: Not downloaded")

    # Language support
    if model_name.endswith(".en"):
        print(f"Languages: English only")
    else:
        print(f"Languages: Multilingual (auto-detect)")

    # Performance estimates (Apple Silicon)
    speed_estimates = {
        "tiny": "~100ms for 5s audio",
        "tiny.en": "~100ms for 5s audio",
        "base": "~200ms for 5s audio",
        "base.en": "~200ms for 5s audio",
        "small": "~500ms for 5s audio",
        "small.en": "~500ms for 5s audio",
        "medium": "~1s for 5s audio",
        "medium.en": "~1s for 5s audio",
        "large-v1": "~2s for 5s audio",
        "large-v2": "~2s for 5s audio",
        "large-v3": "~2s for 5s audio",
    }
    print(f"Speed (Apple Silicon): {speed_estimates.get(model_name, 'N/A')}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="caw-models",
        description="Manage whisper.cpp models for Context-Aware Whisper local transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  caw-models list                    List all models and status
  caw-models download base.en        Download base.en model
  caw-models download small.en -f    Force re-download
  caw-models info base.en            Show model details

Recommended models:
  base.en   - Best balance of speed and accuracy (English)
  small.en  - Better accuracy, slower (English)
  tiny.en   - Fastest, for quick testing (English)
        """
    )

    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Custom models directory (default: ~/.cache/whisper)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List available models and their download status"
    )

    # download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download a whisper model"
    )
    download_parser.add_argument(
        "model",
        type=str,
        help="Model name to download (e.g., base.en, small.en)"
    )
    download_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force re-download even if model exists"
    )

    # info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show detailed information about a model"
    )
    info_parser.add_argument(
        "model",
        type=str,
        help="Model name to show info for"
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for model manager CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 0

    if parsed.command == "list":
        list_models(parsed.models_dir)
        return 0

    elif parsed.command == "download":
        success = download_model(
            parsed.model,
            parsed.models_dir,
            force=parsed.force
        )
        return 0 if success else 1

    elif parsed.command == "info":
        show_model_info(parsed.model, parsed.models_dir)
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
