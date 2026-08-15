"""친구 UUID 목록 파싱."""

from src.config import parse_receiver_uuids


class TestParseReceiverUuids:
    def test_empty_string_means_send_to_self(self):
        assert parse_receiver_uuids("") == ()

    def test_single_uuid(self):
        assert parse_receiver_uuids("abc-123") == ("abc-123",)

    def test_multiple_uuids_split_on_comma(self):
        assert parse_receiver_uuids("uuid-1,uuid-2") == ("uuid-1", "uuid-2")

    def test_whitespace_around_uuids_is_trimmed(self):
        assert parse_receiver_uuids(" uuid-1 , uuid-2 ") == ("uuid-1", "uuid-2")

    def test_blank_entries_are_dropped(self):
        assert parse_receiver_uuids("uuid-1,,uuid-2,") == ("uuid-1", "uuid-2")
