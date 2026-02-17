"""
Unit tests for the feedback regex pattern.
Tests validate the FEEDBACK_PREFIX regex against various input formats.
"""

import re
import pytest
from app.core.config import constants


class TestFeedbackRegex:
    """Test suite for the FEEDBACK_PREFIX regex pattern"""

    @pytest.fixture
    def feedback_pattern(self):
        """Fixture providing the feedback regex pattern"""
        return constants.FEEDBACK_PREFIX

    def test_simple_feedback_with_colon(self, feedback_pattern):
        """Test simple 'feedback:' format with text after colon"""
        text = "feedback: um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_with_hyphen(self, feedback_pattern):
        """Test 'feedback -' format with text after hyphen"""
        text = "feedback - um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_no_space_colon(self, feedback_pattern):
        """Test 'feedback:' with no space after colon"""
        text = "feedback:um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_multiple_colons(self, feedback_pattern):
        """Test 'feedback::' with double colon"""
        text = "feedback::um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_newline_before_text(self, feedback_pattern):
        """Test 'feedback' with newline before text"""
        text = "feedback \n- um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_parentheses(self, feedback_pattern):
        """Test '(FeedBack)' format with parentheses"""
        text = "(FeedBack) um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_brackets(self, feedback_pattern):
        """Test '[feedback]:' format with brackets"""
        text = "[feedback]: um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_angle_brackets(self, feedback_pattern):
        """Test '<feedback> -' format with angle brackets"""
        text = "<feedback> - um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_bold(self, feedback_pattern):
        """Test '**feedback** -' format with bold text"""
        text = "**feedback** - um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_underscore(self, feedback_pattern):
        """Test '_feedback_' format with underscores"""
        text = "_feedback_ - um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_italic(self, feedback_pattern):
        """Test '*feedback*' format with italics"""
        text = "*feedback* - um dolor sit amet, consectetur adipiscing elit"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_case_insensitive_uppercase(self, feedback_pattern):
        """Test case insensitivity with uppercase FEEDBACK"""
        text = "FEEDBACK: test feedback message"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_case_insensitive_mixed(self, feedback_pattern):
        """Test case insensitivity with mixed case FeedBack"""
        text = "FeedBack: test feedback message"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_with_leading_spaces(self, feedback_pattern):
        """Test feedback with leading spaces before the keyword"""
        text = "   feedback: test message"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_not_feedback_wrong_keyword(self, feedback_pattern):
        """Test that non-feedback keywords don't match"""
        text = "question: what is the answer"
        assert not re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_not_feedback_partial_match(self, feedback_pattern):
        """Test that partial feedback keyword doesn't match at start"""
        text = "my feedback on this"
        assert not re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_empty_text_after(self, feedback_pattern):
        """Test feedback with no text after the delimiter"""
        text = "feedback:"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_only_whitespace_after(self, feedback_pattern):
        """Test feedback with only whitespace after"""
        text = "feedback:   "
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_with_emoji(self, feedback_pattern):
        """Test feedback with emoji delimiter"""
        text = "feedback: 👍 test"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_tab_delimiter(self, feedback_pattern):
        """Test feedback with tab as delimiter"""
        text = "feedback\ttest message"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_with_many_leading_spaces(self, feedback_pattern):
        """Test feedback with maximum allowed leading spaces (up to 10)"""
        text = "          feedback: test message"  # 10 spaces
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

    def test_feedback_with_many_trailing_spaces(self, feedback_pattern):
        """Test feedback with spaces after the keyword"""
        text = "feedback          : test message"
        assert re.match(feedback_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
