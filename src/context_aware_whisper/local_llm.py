"""
Local LLM Module
Manages MLX-based local language model for text cleanup.

Uses Apple Silicon's MLX framework for fast local inference.
Supports Phi-3-mini and other MLX-compatible models.
"""

import logging
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Singleton model instance for lazy loading
_model: Optional[Any] = None
_tokenizer: Optional[Any] = None
_current_model_name: Optional[str] = None


def is_available() -> bool:
    """
    Check if MLX is available on this system.

    Returns:
        True if MLX and mlx-lm are installed and importable.
    """
    try:
        import mlx  # noqa: F401
        import mlx_lm  # noqa: F401
        return True
    except ImportError:
        return False


def get_model(
    model_name: str = "mlx-community/Phi-3-mini-4k-instruct-4bit"
) -> Tuple[Any, Any]:
    """
    Get or load the local LLM model (lazy loading).

    Uses singleton pattern - model is loaded once and reused.
    If a different model is requested, the old one is unloaded first.

    Args:
        model_name: HuggingFace model identifier for MLX model.
                   Default: mlx-community/Phi-3-mini-4k-instruct-4bit

    Returns:
        Tuple of (model, tokenizer)

    Raises:
        ImportError: If MLX is not installed.
        Exception: If model loading fails.
    """
    global _model, _tokenizer, _current_model_name

    # If a different model is requested, unload the current one
    if _current_model_name is not None and _current_model_name != model_name:
        logger.info(f"Switching model from {_current_model_name} to {model_name}")
        unload_model()

    if _model is None:
        try:
            from mlx_lm import load

            logger.info(f"Loading local model: {model_name}")
            _model, _tokenizer = load(model_name)
            _current_model_name = model_name
            logger.info("Local model loaded successfully")

        except ImportError:
            logger.error("MLX not installed. Install with: pip install mlx mlx-lm")
            raise
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    return _model, _tokenizer


def generate(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.1,
    model_name: str = "mlx-community/Phi-3-mini-4k-instruct-4bit",
) -> str:
    """
    Generate text using the local LLM.

    Args:
        prompt: Input prompt.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature (lower = more deterministic).
        model_name: Model to use.

    Returns:
        Generated text.

    Raises:
        ImportError: If MLX is not installed.
        Exception: If generation fails.
    """
    try:
        from mlx_lm import generate as mlx_generate

        model, tokenizer = get_model(model_name)

        response = mlx_generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            temp=temperature,
            verbose=False,
        )

        return response.strip()

    except Exception as e:
        logger.error(f"Local LLM generation failed: {e}")
        raise


def unload_model() -> None:
    """
    Unload model from memory.

    Useful for freeing up GPU/RAM when the model is no longer needed.
    """
    global _model, _tokenizer, _current_model_name

    if _model is not None:
        logger.info(f"Unloading model: {_current_model_name}")

    _model = None
    _tokenizer = None
    _current_model_name = None


def get_current_model_name() -> Optional[str]:
    """
    Get the name of the currently loaded model.

    Returns:
        Model name if loaded, None otherwise.
    """
    return _current_model_name
