"""
Unit tests for the feedback regex pattern.
Tests validate the FEEDBACK_PREFIX regex against various input formats.
"""

import html
import re
import pytest
from app.core.config import constants


class TestFeedbackRegex:
    """Test suite for the FEEDBACK_PREFIX regex pattern"""

    def isMatch(self, pattern, text):
        """Helper method to check if the pattern matches the text"""
        formatted_text = html.unescape(text)
        return re.match(pattern, formatted_text, re.IGNORECASE | re.DOTALL | re.MULTILINE) is not None

    @pytest.fixture
    def feedback_pattern(self):
        """Fixture providing the feedback regex pattern"""
        return constants.FEEDBACK_PREFIX

    def test_simple_feedback_with_colon(self, feedback_pattern):
        """Test simple 'feedback:' format with text after colon"""
        text = "feedback: um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_with_hyphen(self, feedback_pattern):
        """Test 'feedback -' format with text after hyphen"""
        text = "feedback - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_no_space_colon(self, feedback_pattern):
        """Test 'feedback:' with no space after colon"""
        text = "feedback:um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_multiple_colons(self, feedback_pattern):
        """Test 'feedback::' with double colon"""
        text = "feedback::um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_newline_before_text(self, feedback_pattern):
        """Test 'feedback' with newline before text"""
        text = "feedback \n- um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_parentheses(self, feedback_pattern):
        """Test '(FeedBack)' format with parentheses"""
        text = "(FeedBack) um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_parentheses_encoded(self, feedback_pattern):
        """Test '&#40;FeedBack&#41;' format with encoded parentheses"""
        text = "&#40;FeedBack&#41; um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_brackets(self, feedback_pattern):
        """Test '[feedback]:' format with brackets"""
        text = "[feedback]: um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_brackets_encoded(self, feedback_pattern):
        """Test '&#91;feedback&#93;:' format with encoded brackets"""
        text = "&#91;feedback&#93;: um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_angle_brackets(self, feedback_pattern):
        """Test '<feedback> -' format with angle brackets"""
        text = "<feedback> - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_angle_brackets_encoded(self, feedback_pattern):
        """Test '&lt;feedback> -' format with angle brackets"""
        text = "&lt;feedback&gt; - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_bold(self, feedback_pattern):
        """Test '**feedback** -' format with bold text"""
        text = "**feedback** - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_bold_encoded(self, feedback_pattern):
        """Test '&#42;&#42;feedback&#42;&#42; -' format with encoded bold text"""
        text = "&#42;&#42;feedback&#42;&#42; - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_underscore(self, feedback_pattern):
        """Test '_feedback_' format with underscores"""
        text = "_feedback_ - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_underscore_encoded(self, feedback_pattern):
        """Test '&#95;feedback&#95;' format with encoded underscores"""
        text = "&#95;feedback&#95; - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_italic(self, feedback_pattern):
        """Test '*feedback*' format with italics"""
        text = "*feedback* - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_italic_encoded(self, feedback_pattern):
        """Test '&#42;feedback&#42;' format with encoded italics"""
        text = "&#42;feedback&#42; - um dolor sit amet, consectetur adipiscing elit"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_case_insensitive_uppercase(self, feedback_pattern):
        """Test case insensitivity with uppercase FEEDBACK"""
        text = "FEEDBACK: test feedback message"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_case_insensitive_mixed(self, feedback_pattern):
        """Test case insensitivity with mixed case FeedBack"""
        text = "FeedBack: test feedback message"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_with_leading_spaces(self, feedback_pattern):
        """Test feedback with leading spaces before the keyword"""
        text = "   feedback: test message"
        assert self.isMatch(feedback_pattern, text)

    def test_not_feedback_wrong_keyword(self, feedback_pattern):
        """Test that non-feedback keywords don't match"""
        text = "question: what is the answer"
        assert not self.isMatch(feedback_pattern, text)

    def test_not_feedback_partial_match(self, feedback_pattern):
        """Test that partial feedback keyword doesn't match at start"""
        text = "my feedback on this"
        assert not self.isMatch(feedback_pattern, text)

    def test_feedback_empty_text_after(self, feedback_pattern):
        """Test feedback with no text after the delimiter"""
        text = "feedback:"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_only_whitespace_after(self, feedback_pattern):
        """Test feedback with only whitespace after"""
        text = "feedback:   "
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_with_emoji(self, feedback_pattern):
        """Test feedback with emoji delimiter"""
        text = "feedback: 👍 test"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_tab_delimiter(self, feedback_pattern):
        """Test feedback with tab as delimiter"""
        text = "feedback\ttest message"
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_with_many_leading_spaces(self, feedback_pattern):
        """Test feedback with maximum allowed leading spaces (up to 10)"""
        text = "          feedback: test message"  # 10 spaces
        assert self.isMatch(feedback_pattern, text)

    def test_feedback_with_many_trailing_spaces(self, feedback_pattern):
        """Test feedback with spaces after the keyword"""
        text = "feedback          : test message"
        assert self.isMatch(feedback_pattern, text)
