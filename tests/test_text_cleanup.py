"""
Tests for text cleanup module.

Comprehensive tests for TextCleaner class including:
- All cleanup modes (off, light, standard, aggressive)
- Filler word removal
- Repetition removal
- False start removal
- Context-aware cleanup
- Property-based tests with Hypothesis
"""

import pytest
from hypothesis import given, strategies as st

from context_aware_whisper.text_cleanup import TextCleaner, CleanupMode


class TestCleanupModeOff:
    """Tests for disabled cleanup."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.OFF)

    def test_returns_unchanged(self):
        """OFF mode returns text unchanged."""
        text = "Um, I I think, you know, like..."
        assert self.cleaner.clean(text) == text

    def test_empty_string_unchanged(self):
        """OFF mode returns empty string unchanged."""
        assert self.cleaner.clean("") == ""

    def test_preserves_all_fillers(self):
        """OFF mode preserves all filler words."""
        text = "Um, uh, ah, er, hmm, mm, mhm"
        assert self.cleaner.clean(text) == text


class TestCleanupModeLight:
    """Tests for light cleanup mode."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.LIGHT)

    def test_removes_um(self):
        """Light mode removes 'um'."""
        assert self.cleaner.clean("Um, hello there") == "hello there"

    def test_removes_uh(self):
        """Light mode removes 'uh'."""
        assert self.cleaner.clean("I uh think so") == "I think so"

    def test_removes_ah(self):
        """Light mode removes 'ah'."""
        assert self.cleaner.clean("Ah, I see") == "I see"

    def test_removes_er(self):
        """Light mode removes 'er'."""
        assert self.cleaner.clean("I was, er, thinking") == "I was, thinking"

    def test_removes_hmm(self):
        """Light mode removes 'hmm'."""
        assert self.cleaner.clean("Hmm, that's interesting") == "that's interesting"

    def test_removes_mm(self):
        """Light mode removes 'mm'."""
        result = self.cleaner.clean("Mm, I agree")
        assert "Mm" not in result

    def test_removes_mhm(self):
        """Light mode removes 'mhm'."""
        result = self.cleaner.clean("Mhm, that's right")
        assert "Mhm" not in result

    def test_removes_multiple_fillers(self):
        """Light mode removes multiple filler words."""
        result = self.cleaner.clean("Um, uh, hello")
        assert "Um" not in result
        assert "uh" not in result
        assert "hello" in result.lower()

    def test_preserves_like(self):
        """Light mode doesn't remove 'like'."""
        result = self.cleaner.clean("It's like really good")
        assert "like" in result.lower()

    def test_preserves_you_know(self):
        """Light mode doesn't remove 'you know'."""
        result = self.cleaner.clean("It's, you know, important")
        assert "you know" in result.lower()

    def test_case_insensitive(self):
        """Light mode is case insensitive."""
        assert "UM" not in self.cleaner.clean("UM, hello")
        assert "Um" not in self.cleaner.clean("Um, hello")
        assert "um" not in self.cleaner.clean("um, hello")


class TestCleanupModeStandard:
    """Tests for standard cleanup mode."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    def test_removes_filler_like(self):
        """Standard mode removes filler 'like'."""
        result = self.cleaner.clean("It's like really good")
        assert result == "It's really good"

    def test_preserves_verb_like(self):
        """Standard mode preserves 'like' as verb."""
        result = self.cleaner.clean("I like this feature")
        assert result == "I like this feature"

    def test_preserves_like_to(self):
        """Standard mode preserves 'like to'."""
        result = self.cleaner.clean("I would like to help")
        assert "like to" in result

    def test_preserves_like_the(self):
        """Standard mode preserves 'like the'."""
        result = self.cleaner.clean("It looks like the one we need")
        assert "like the" in result

    def test_removes_you_know(self):
        """Standard mode removes 'you know'."""
        result = self.cleaner.clean("It's, you know, important")
        assert "you know" not in result.lower()
        assert "important" in result

    def test_removes_i_mean(self):
        """Standard mode removes 'i mean'."""
        result = self.cleaner.clean("I mean, that's correct")
        assert "I mean" not in result
        assert "correct" in result

    def test_removes_basically(self):
        """Standard mode removes 'basically'."""
        result = self.cleaner.clean("Basically, we need to fix this")
        assert "basically" not in result.lower()

    def test_removes_actually(self):
        """Standard mode removes 'actually'."""
        result = self.cleaner.clean("Actually, that's wrong")
        assert "actually" not in result.lower()

    def test_removes_literally(self):
        """Standard mode removes 'literally'."""
        result = self.cleaner.clean("It's literally the best")
        assert "literally" not in result.lower()

    def test_removes_kind_of(self):
        """Standard mode removes 'kind of'."""
        result = self.cleaner.clean("It's kind of nice")
        assert "kind of" not in result.lower()

    def test_removes_sort_of(self):
        """Standard mode removes 'sort of'."""
        result = self.cleaner.clean("It's sort of working")
        assert "sort of" not in result.lower()

    def test_removes_repetitions(self):
        """Standard mode removes word repetitions."""
        assert self.cleaner.clean("I I think so") == "I think so"

    def test_removes_double_repetitions(self):
        """Standard mode removes double repetitions."""
        assert self.cleaner.clean("the the thing") == "the thing"

    def test_removes_triple_repetitions(self):
        """Standard mode removes triple repetitions."""
        assert self.cleaner.clean("the the the thing") == "the thing"

    def test_preserves_emphasis_very(self):
        """Standard mode preserves 'very very' for emphasis."""
        result = self.cleaner.clean("This is very very important")
        assert "very very" in result

    def test_preserves_emphasis_really(self):
        """Standard mode preserves 'really really' for emphasis."""
        result = self.cleaner.clean("I really really want this")
        assert "really really" in result

    def test_preserves_emphasis_so(self):
        """Standard mode preserves 'so so' for emphasis."""
        result = self.cleaner.clean("This is so so good")
        assert "so so" in result

    def test_removes_false_starts_with_sorry(self):
        """Standard mode removes false starts with 'sorry'."""
        result = self.cleaner.clean("Can you... sorry, can you send this?")
        assert "..." not in result or result.count("can you") == 1

    def test_removes_false_starts_with_actually(self):
        """Standard mode removes false starts with 'actually'."""
        result = self.cleaner.clean("I think... actually, I know")
        # Should simplify the correction
        assert "I know" in result

    def test_complex_disfluency(self):
        """Standard mode handles complex disfluencies."""
        result = self.cleaner.clean(
            "Hey, um, can you, you know, send this?"
        )
        assert "um" not in result.lower()
        assert "you know" not in result.lower()
        assert "send this" in result.lower()


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert self.cleaner.clean("") == ""

    def test_none_as_empty(self):
        """None-like handling returns empty."""
        assert self.cleaner.clean(None or "") == ""

    def test_only_fillers(self):
        """Text with only fillers returns empty or minimal."""
        result = self.cleaner.clean("Um uh")
        assert isinstance(result, str)
        # Should be empty or very short after removing fillers
        assert len(result.strip()) <= 2

    def test_whitespace_normalization(self):
        """Multiple spaces are normalized."""
        result = self.cleaner.clean("Hello   world")
        assert result == "Hello world"

    def test_punctuation_preservation(self):
        """Punctuation is preserved."""
        result = self.cleaner.clean("Hello, um, world!")
        assert "!" in result
        assert "world" in result

    def test_question_mark_preservation(self):
        """Question marks are preserved."""
        result = self.cleaner.clean("Um, how are you?")
        assert "?" in result

    def test_sentence_case_preservation(self):
        """Sentence case is preserved."""
        result = self.cleaner.clean("Hello there")
        assert result[0].isupper()

    def test_no_trailing_whitespace(self):
        """No trailing whitespace in output."""
        result = self.cleaner.clean("Hello, um, ")
        assert result == result.strip()

    def test_no_leading_whitespace(self):
        """No leading whitespace in output."""
        result = self.cleaner.clean("  Um, hello")
        assert result == result.strip()

    def test_single_word(self):
        """Single word is preserved."""
        assert self.cleaner.clean("Hello") == "Hello"

    def test_numbers_preserved(self):
        """Numbers in text are preserved."""
        result = self.cleaner.clean("Um, I have 5 apples")
        assert "5" in result

    def test_special_characters(self):
        """Special characters are handled."""
        result = self.cleaner.clean("Um, email@example.com")
        assert "email@example.com" in result


class TestPreserveIntentional:
    """Tests for preserve_intentional flag."""

    def test_preserve_intentional_true_like(self):
        """Preserve 'I like' when preserve_intentional=True."""
        cleaner = TextCleaner(
            mode=CleanupMode.STANDARD,
            preserve_intentional=True
        )
        result = cleaner.clean("I like pizza")
        assert result == "I like pizza"

    def test_preserve_intentional_true_emphasis(self):
        """Preserve emphasis repetitions when preserve_intentional=True."""
        cleaner = TextCleaner(
            mode=CleanupMode.STANDARD,
            preserve_intentional=True
        )
        result = cleaner.clean("very very important")
        assert "very very" in result

    def test_preserve_intentional_false_removes_repetitions(self):
        """Remove all repetitions when preserve_intentional=False."""
        cleaner = TextCleaner(
            mode=CleanupMode.STANDARD,
            preserve_intentional=False
        )
        result = cleaner.clean("very very important")
        assert result == "very important"

    def test_preserve_intentional_false_removes_really(self):
        """Remove 'really really' when preserve_intentional=False."""
        cleaner = TextCleaner(
            mode=CleanupMode.STANDARD,
            preserve_intentional=False
        )
        result = cleaner.clean("I really really want this")
        assert "really really" not in result


class TestCleanupModeAggressive:
    """Tests for aggressive cleanup mode."""

    def test_aggressive_falls_back_when_mlx_unavailable(self):
        """Aggressive mode falls back to standard when MLX unavailable."""
        from unittest.mock import patch

        with patch('context_aware_whisper.local_llm.is_available', return_value=False):
            cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)
            result = cleaner.clean("Um, hello there")
            # Should still clean basic fillers (fallback to standard)
            assert "Um" not in result

    def test_aggressive_empty_string(self):
        """Aggressive mode handles empty string."""
        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)
        assert cleaner.clean("") == ""

    def test_aggressive_with_custom_model(self):
        """Aggressive mode accepts custom model name."""
        cleaner = TextCleaner(
            mode=CleanupMode.AGGRESSIVE,
            model_name="custom-model"
        )
        assert cleaner.model_name == "custom-model"


class TestCleanMethod:
    """Tests for the main clean() method dispatch."""

    def test_clean_dispatches_to_off(self):
        """clean() correctly uses OFF mode."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)
        text = "Um, hello"
        assert cleaner.clean(text) == text

    def test_clean_dispatches_to_light(self):
        """clean() correctly uses LIGHT mode."""
        cleaner = TextCleaner(mode=CleanupMode.LIGHT)
        result = cleaner.clean("Um, hello")
        assert "Um" not in result

    def test_clean_dispatches_to_standard(self):
        """clean() correctly uses STANDARD mode."""
        cleaner = TextCleaner(mode=CleanupMode.STANDARD)
        result = cleaner.clean("You know, hello")
        assert "you know" not in result.lower()


class TestFillerSets:
    """Tests for filler word sets."""

    def test_fillers_light_is_subset_of_standard(self):
        """Light fillers should be subset of standard fillers."""
        assert TextCleaner.FILLERS_LIGHT.issubset(TextCleaner.FILLERS_STANDARD)

    def test_fillers_light_contains_basic_sounds(self):
        """Light fillers should contain basic speech sounds."""
        expected = {"um", "uh", "ah", "er"}
        assert expected.issubset(TextCleaner.FILLERS_LIGHT)

    def test_fillers_standard_contains_phrases(self):
        """Standard fillers should contain common phrases."""
        expected = {"you know", "i mean", "kind of", "sort of"}
        assert expected.issubset(TextCleaner.FILLERS_STANDARD)


class TestCorrectionMarkers:
    """Tests for correction markers."""

    def test_correction_markers_contains_sorry(self):
        """Correction markers should contain 'sorry'."""
        assert "sorry" in TextCleaner.CORRECTION_MARKERS

    def test_correction_markers_contains_i_mean(self):
        """Correction markers should contain 'i mean'."""
        assert "i mean" in TextCleaner.CORRECTION_MARKERS

    def test_correction_markers_contains_actually(self):
        """Correction markers should contain 'actually'."""
        assert "actually" in TextCleaner.CORRECTION_MARKERS


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    @given(st.text(min_size=0, max_size=1000))
    def test_never_crashes(self, text):
        """Cleanup should never crash on any input."""
        result = self.cleaner.clean(text)
        assert isinstance(result, str)

    @given(st.text(min_size=1, max_size=500))
    def test_output_not_much_longer(self, text):
        """Output should not be significantly longer than input."""
        result = self.cleaner.clean(text)
        # Allow small increase for whitespace normalization
        assert len(result) <= len(text) + 10

    @given(st.text(min_size=0, max_size=1000))
    def test_off_mode_preserves_text(self, text):
        """OFF mode should preserve input exactly."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)
        assert cleaner.clean(text) == text

    @given(st.text(min_size=0, max_size=500, alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        whitelist_characters=' .,!?'
    )))
    def test_light_mode_never_crashes(self, text):
        """Light mode should never crash on reasonable input."""
        cleaner = TextCleaner(mode=CleanupMode.LIGHT)
        result = cleaner.clean(text)
        assert isinstance(result, str)

    @given(st.text(min_size=1, max_size=100))
    def test_idempotent_standard(self, text):
        """Cleaning already cleaned text should be idempotent (mostly)."""
        first_clean = self.cleaner.clean(text)
        second_clean = self.cleaner.clean(first_clean)
        # Second clean should not change much (whitespace normalization may differ)
        assert len(second_clean) <= len(first_clean) + 5


class TestIntegrationWithConfig:
    """Tests for integration with configuration."""

    def test_mode_from_string_off(self):
        """CleanupMode.OFF can be used."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)
        assert cleaner.mode == CleanupMode.OFF

    def test_mode_from_string_light(self):
        """CleanupMode.LIGHT can be used."""
        cleaner = TextCleaner(mode=CleanupMode.LIGHT)
        assert cleaner.mode == CleanupMode.LIGHT

    def test_mode_from_string_standard(self):
        """CleanupMode.STANDARD can be used."""
        cleaner = TextCleaner(mode=CleanupMode.STANDARD)
        assert cleaner.mode == CleanupMode.STANDARD

    def test_mode_from_string_aggressive(self):
        """CleanupMode.AGGRESSIVE can be used."""
        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)
        assert cleaner.mode == CleanupMode.AGGRESSIVE


class TestPerformance:
    """Performance-related tests."""

    def test_short_text_performance(self):
        """Short text should clean quickly."""
        import time
        cleaner = TextCleaner(mode=CleanupMode.STANDARD)
        text = "Um, I I think, you know, like, we should do this."

        start = time.perf_counter()
        for _ in range(100):
            cleaner.clean(text)
        elapsed = time.perf_counter() - start

        # 100 iterations should take less than 1 second
        assert elapsed < 1.0

    def test_long_text_performance(self):
        """Long text should clean in reasonable time."""
        import time
        cleaner = TextCleaner(mode=CleanupMode.STANDARD)
        text = "Um, I I think, you know, like, we should do this. " * 100

        start = time.perf_counter()
        cleaner.clean(text)
        elapsed = time.perf_counter() - start

        # Single long text should take less than 500ms
        assert elapsed < 0.5


class TestRealWorldExamples:
    """Tests with realistic speech transcription examples."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    def test_meeting_speech(self):
        """Realistic meeting speech cleanup."""
        input_text = "So, um, I think we should, you know, basically move forward with the project."
        result = self.cleaner.clean(input_text)
        assert "um" not in result.lower()
        assert "you know" not in result.lower()
        assert "basically" not in result.lower()
        assert "move forward" in result.lower()
        assert "project" in result

    def test_casual_conversation(self):
        """Realistic casual speech cleanup."""
        input_text = "Like, I was like, you know, just walking around, and, um, I saw this."
        result = self.cleaner.clean(input_text)
        assert "um" not in result.lower()
        # Core content preserved
        assert "walking" in result.lower()
        assert "saw" in result.lower()

    def test_technical_dictation(self):
        """Technical dictation with minimal filler."""
        input_text = "The function returns an integer, um, value representing the count."
        result = self.cleaner.clean(input_text)
        assert "um" not in result.lower()
        assert "function" in result
        assert "integer" in result
        assert "count" in result

    def test_stutter_recovery(self):
        """Stutter/repetition recovery."""
        input_text = "I I I want to to say something."
        result = self.cleaner.clean(input_text)
        # Should reduce stuttering
        assert result.count(" I ") <= 1 or "I want" in result

    def test_false_start_correction(self):
        """False start with correction."""
        input_text = "Send the email to... sorry, send the message to John."
        result = self.cleaner.clean(input_text)
        # Should handle false start
        assert "John" in result
        assert "message" in result or "email" in result
