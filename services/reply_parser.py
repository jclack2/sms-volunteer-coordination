"""
Reply parsing service for SMS responses
"""


class ReplyParser:
    """Parse incoming SMS replies"""

    # Standard affirmative responses
    STANDARD_YES = [
        'yes', 'y', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay',
        'available', 'can do', 'i can', "i'm available", 'count me in',
        'im in', "i'm in", 'sounds good'
    ]

    # Standard negative responses
    STANDARD_NO = [
        'no', 'n', 'nope', 'nah', 'cant', "can't", 'cannot',
        'not available', 'unavailable', 'sorry', 'unable'
    ]

    # Opt-in keywords
    OPT_IN_JOIN = ['join', 'subscribe', 'start']
    OPT_IN_CONFIRM = ['yes', 'y', 'confirm']

    # Opt-out keywords
    OPT_OUT = ['stop', 'unsubscribe', 'cancel', 'quit', 'end']

    # Status query
    STATUS_QUERY = ['status', 'info', 'information']

    # Cancellation
    CANCEL = ['cancel', 'drop', 'remove', 'withdraw']

    @staticmethod
    def normalize_text(text):
        """Normalize text for comparison"""
        if not text:
            return ''
        return text.lower().strip()

    @classmethod
    def parse_response(cls, text, custom_yes=None, custom_no=None):
        """
        Parse a volunteer response

        Args:
            text: SMS message text
            custom_yes: List of custom affirmative strings for this event
            custom_no: List of custom negative strings for this event

        Returns:
            tuple: (parsed_response, requires_review)
                parsed_response: 'YES', 'NO', or 'UNKNOWN'
                requires_review: True if manual review needed
        """
        normalized = cls.normalize_text(text)

        # Build complete lists
        yes_list = cls.STANDARD_YES[:]
        no_list = cls.STANDARD_NO[:]

        if custom_yes:
            yes_list.extend([cls.normalize_text(s) for s in custom_yes if s])

        if custom_no:
            no_list.extend([cls.normalize_text(s) for s in custom_no if s])

        # Check for exact match first
        if normalized in yes_list:
            return 'YES', False

        if normalized in no_list:
            return 'NO', False

        # Check if message starts with yes/no phrase
        for phrase in yes_list:
            if normalized.startswith(phrase):
                # If there's additional text, flag for review
                if len(normalized) > len(phrase) + 1:
                    return 'YES', True
                return 'YES', False

        for phrase in no_list:
            if normalized.startswith(phrase):
                if len(normalized) > len(phrase) + 1:
                    return 'NO', True
                return 'NO', False

        # Unknown response - requires review
        return 'UNKNOWN', True

    @classmethod
    def is_opt_in_join(cls, text):
        """Check if message is JOIN request"""
        normalized = cls.normalize_text(text)
        return normalized in cls.OPT_IN_JOIN

    @classmethod
    def is_opt_in_confirm(cls, text):
        """Check if message is opt-in confirmation"""
        normalized = cls.normalize_text(text)
        return normalized in cls.OPT_IN_CONFIRM

    @classmethod
    def is_opt_out(cls, text):
        """Check if message is opt-out request"""
        normalized = cls.normalize_text(text)
        return normalized in cls.OPT_OUT

    @classmethod
    def is_status_query(cls, text):
        """Check if message is status query"""
        normalized = cls.normalize_text(text)
        return normalized in cls.STATUS_QUERY

    @classmethod
    def is_cancellation(cls, text):
        """Check if message is cancellation"""
        normalized = cls.normalize_text(text)
        return normalized in cls.CANCEL
