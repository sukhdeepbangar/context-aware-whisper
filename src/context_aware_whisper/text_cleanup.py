"""
Text Cleanup Module
Removes speech disfluencies from transcribed text.
"""

import re
import logging
from enum import Enum, auto
from typing import Optional, Set, List

from context_aware_whisper.exceptions import TextCleanupError


logger = logging.getLogger(__name__)


class CleanupMode(Enum):
    """Text cleanup aggressiveness levels."""
    OFF = auto()        # No cleanup
    LIGHT = auto()      # Only obvious fillers (um, uh, ah)
    STANDARD = auto()   # Fillers + repetitions + false starts
    AGGRESSIVE = auto() # LLM-powered cleanup (requires API)


class TextCleaner:
    """
    Cleans speech disfluencies from transcribed text.

    Pipeline: Transcriber -> TextCleaner -> OutputHandler
    """

    # Filler words for light mode
    FILLERS_LIGHT: Set[str] = {
        "um", "uh", "ah", "er", "hmm", "mm", "mhm",
    }

    # Additional fillers for standard mode
    FILLERS_STANDARD: Set[str] = FILLERS_LIGHT | {
        "like", "you know", "i mean", "so", "basically",
        "actually", "literally", "right", "okay", "well",
        "anyway", "you see", "kind of", "sort of",
    }

    # Markers indicating false starts
    CORRECTION_MARKERS: List[str] = [
        "sorry", "i mean", "no wait", "actually",
        "let me rephrase", "correction", "rather",
    ]

    # LLM prompt for aggressive mode (grammar and tense correction)
    LLM_PROMPT = """Clean and correct this speech transcription.

Tasks:
1. Remove filler words (um, uh, like, you know, basically)
2. Remove false starts and repetitions
3. Fix grammar errors
4. Correct tense inconsistencies
5. Preserve the speaker's intended meaning and tone

Input: {text}

Output only the corrected text, nothing else:"""

    # Default local model for aggressive mode
    DEFAULT_MODEL = "mlx-community/Phi-3-mini-4k-instruct-4bit"

    # Default chunk size for batch processing (characters)
    # ~500 chars = ~100-125 tokens, safe for most models
    DEFAULT_CHUNK_SIZE = 500

    def __init__(
        self,
        mode: CleanupMode = CleanupMode.STANDARD,
        model_name: Optional[str] = None,
        preserve_intentional: bool = True,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ):
        """
        Initialize text cleaner.

        Args:
            mode: Cleanup aggressiveness level
            model_name: Local model name for AGGRESSIVE mode (MLX model).
                       Default: mlx-community/Phi-3-mini-4k-instruct-4bit
            preserve_intentional: Preserve intentional patterns
            chunk_size: Max characters per chunk for batch processing in
                       AGGRESSIVE mode. Default: 500 (~100-125 tokens)
        """
        self.mode = mode
        self.model_name = model_name or self.DEFAULT_MODEL
        self.preserve_intentional = preserve_intentional
        self.chunk_size = chunk_size

        # Pre-compile regex patterns for performance
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._repetition_pattern = re.compile(
            r'\b(\w+)(?:\s+\1){1,3}\b',
            re.IGNORECASE
        )
        self._ellipsis_pattern = re.compile(r'\.{2,}')
        # Sentence boundary pattern for chunk splitting
        self._sentence_boundary = re.compile(r'(?<=[.!?])\s+')

    def clean(self, text: str) -> str:
        """
        Clean speech disfluencies from text.

        Args:
            text: Raw transcription text

        Returns:
            Cleaned text with disfluencies removed
        """
        if self.mode == CleanupMode.OFF:
            return text
        elif self.mode == CleanupMode.LIGHT:
            return self.clean_light(text)
        elif self.mode == CleanupMode.STANDARD:
            return self.clean_standard(text)
        elif self.mode == CleanupMode.AGGRESSIVE:
            return self.clean_aggressive(text)
        else:
            return text

    def clean_light(self, text: str) -> str:
        """Remove only obvious filler words (um, uh, ah)."""
        if not text:
            return text

        result = text

        # Remove standalone fillers with word boundaries
        for filler in sorted(self.FILLERS_LIGHT, key=len, reverse=True):
            pattern = rf'\b{re.escape(filler)}\b,?\s*'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        return self._normalize_whitespace(result)

    def clean_standard(self, text: str) -> str:
        """Remove fillers, repetitions, and false starts."""
        if not text:
            return text

        result = text

        # Step 1: Remove false starts (text before correction markers)
        result = self._remove_false_starts(result)

        # Step 2: Remove filler words/phrases (context-aware)
        result = self._remove_fillers(result)

        # Step 3: Remove word repetitions
        result = self._remove_repetitions(result)

        # Step 4: Clean up orphaned ellipses
        result = self._clean_ellipses(result)

        return self._normalize_whitespace(result)

    def clean_aggressive(self, text: str) -> str:
        """
        Use local LLM for intelligent cleanup with grammar correction.

        For texts longer than chunk_size, splits into sentence-boundary
        chunks and processes them in batches for better performance.
        """
        if not text:
            return text

        try:
            from context_aware_whisper.local_llm import is_available

            if not is_available():
                logger.warning("MLX not available, falling back to standard cleanup")
                return self.clean_standard(text)

            # Use batch processing for long texts
            if len(text) > self.chunk_size:
                return self._process_in_batches(text)

            return self._clean_single_chunk(text)

        except Exception as e:
            logger.warning(f"Local LLM cleanup failed, using rule-based: {e}")
            return self.clean_standard(text)

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks at sentence boundaries.

        Attempts to keep chunks under chunk_size while respecting
        sentence boundaries. If a single sentence exceeds chunk_size,
        it will be kept as its own chunk.

        Args:
            text: Text to split into chunks.

        Returns:
            List of text chunks.
        """
        if len(text) <= self.chunk_size:
            return [text]

        # Split at sentence boundaries
        sentences = self._sentence_boundary.split(text)
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_len = len(sentence)

            # If adding this sentence would exceed chunk_size
            if current_length + sentence_len + 1 > self.chunk_size:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # If single sentence exceeds chunk_size, add it as its own chunk
                if sentence_len > self.chunk_size:
                    chunks.append(sentence)
                else:
                    current_chunk.append(sentence)
                    current_length = sentence_len
            else:
                current_chunk.append(sentence)
                current_length += sentence_len + 1  # +1 for space

        # Add remaining sentences
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text]

    def _clean_single_chunk(self, text: str) -> str:
        """
        Clean a single chunk of text using the LLM.

        Args:
            text: Text chunk to clean.

        Returns:
            Cleaned text, or standard-cleaned text on failure.
        """
        from context_aware_whisper.local_llm import generate

        cleaned = generate(
            prompt=self.LLM_PROMPT.format(text=text),
            max_tokens=len(text) * 2,
            temperature=0.1,
            model_name=self.model_name,
        )

        # Sanity check: if too much removed, fall back
        if len(cleaned) < len(text) * 0.3:
            logger.warning("LLM removed too much text, falling back to standard")
            return self.clean_standard(text)

        return cleaned

    def _process_in_batches(self, text: str) -> str:
        """
        Process long text by splitting into chunks and cleaning each.

        This approach:
        1. Splits text at sentence boundaries into manageable chunks
        2. Processes each chunk with the LLM
        3. Joins the cleaned chunks back together

        Args:
            text: Long text to process.

        Returns:
            Cleaned text with all chunks processed.
        """
        chunks = self._split_into_chunks(text)
        logger.debug(f"Processing {len(chunks)} chunks for text of length {len(text)}")

        cleaned_chunks: List[str] = []
        for i, chunk in enumerate(chunks):
            try:
                cleaned = self._clean_single_chunk(chunk)
                cleaned_chunks.append(cleaned)
                logger.debug(f"Chunk {i+1}/{len(chunks)}: {len(chunk)} -> {len(cleaned)} chars")
            except Exception as e:
                # On failure for a chunk, fall back to standard cleanup for that chunk
                logger.warning(f"Chunk {i+1} failed, using standard: {e}")
                cleaned_chunks.append(self.clean_standard(chunk))

        result = ' '.join(cleaned_chunks)
        return self._normalize_whitespace(result)

    def _remove_false_starts(self, text: str) -> str:
        """Remove text before correction markers."""
        result = text

        for marker in self.CORRECTION_MARKERS:
            # Pattern: "X... sorry, Y" -> "Y"
            pattern = rf'[^.!?]*?\.\.\.\s*{re.escape(marker)},?\s*'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

            # Pattern: "X, sorry, X" (where X repeats) -> "X"
            pattern = rf'([^,]+),\s*{re.escape(marker)},?\s*\1'
            result = re.sub(pattern, r'\1', result, flags=re.IGNORECASE)

        return result

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words with context awareness."""
        result = text

        for filler in sorted(self.FILLERS_STANDARD, key=len, reverse=True):
            if self.preserve_intentional and filler == "like":
                # Preserve "like" as verb: "I like pizza"
                # Remove "like" as filler: "It's like really good"
                pattern = rf'(?<!\bI\s)\b{re.escape(filler)}\b(?!\s+(?:to|the|a|my|your|this|that|it\b))'
                result = re.sub(pattern + r',?\s*', '', result, flags=re.IGNORECASE)
            elif filler == "so":
                # "so" is tricky - preserve when:
                # 1. At end of phrase: "I think so", "I hope so"
                # 2. As emphasis repetition: "so so good"
                # Remove when at start of sentence or as standalone filler
                # Only remove "so" at beginning of sentence/clause followed by comma or space+word
                pattern = rf'(?:^|\.\s+|,\s*)\bso\b,?\s+(?=[A-Za-z])'
                result = re.sub(pattern, lambda m: m.group(0)[:m.group(0).find('so')], result, flags=re.IGNORECASE)
            else:
                pattern = rf'\b{re.escape(filler)}\b,?\s*'
                result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        return result

    def _remove_repetitions(self, text: str) -> str:
        """Remove consecutive word repetitions."""
        if self.preserve_intentional:
            # Preserve emphasis: "very very important"
            emphasis_words = {'very', 'really', 'so', 'much', 'too', 'super'}

            def replace_repetition(match):
                word = match.group(1).lower()
                if word in emphasis_words:
                    return match.group(0)  # Keep intentional emphasis
                return match.group(1)  # Remove stutter

            return self._repetition_pattern.sub(replace_repetition, text)
        else:
            return self._repetition_pattern.sub(r'\1', text)

    def _clean_ellipses(self, text: str) -> str:
        """Clean up orphaned ellipses."""
        result = re.sub(r'^\s*\.{2,}\s*', '', text)
        result = re.sub(r'\.\s+\.{2,}\s*', '. ', result)
        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace and punctuation."""
        result = re.sub(r' +', ' ', text)
        result = re.sub(r'\s+([.,!?])', r'\1', result)
        return result.strip()
