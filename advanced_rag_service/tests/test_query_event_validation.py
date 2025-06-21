"""
Test suite for enhanced QueryEvent timestamp validation

This module tests the enhanced timestamp validation that has been moved 
from the API layer into the QueryEvent domain model.
"""

import pytest
from datetime import datetime, timezone, timedelta
from advanced_rag import QueryEvent
from error_handling import TemporalProcessingError


def test_query_event_valid_timestamps():
    """Test QueryEvent creation with valid timestamps"""
    print("Testing QueryEvent with valid timestamps...")

    # Use recent past timestamps to avoid future/old validation issues
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    # Test UTC timezone with Z suffix
    utc_timestamp = base_time.isoformat().replace('+00:00', 'Z')
    event1 = QueryEvent(
        camera_id="cam_001",
        timestamp=utc_timestamp,
        label="person"
    )
    assert event1.timestamp == utc_timestamp
    assert event1.camera_id == "cam_001"
    print("   ✅ UTC timestamp with Z suffix works")

    # Test timezone with positive offset (keeping in past)
    offset_time = base_time.replace(tzinfo=timezone(timedelta(hours=2)))
    offset_timestamp = offset_time.isoformat()
    event2 = QueryEvent(
        camera_id="cam_002", 
        timestamp=offset_timestamp,
        label="vehicle"
    )
    assert event2.timestamp == offset_timestamp
    print("   ✅ Timezone with positive offset works")

    # Test with standard +00:00 timezone format instead of negative offset
    utc_plus_format = base_time.replace(tzinfo=timezone.utc).isoformat()
    event3 = QueryEvent(
        camera_id="cam_003",
        timestamp=utc_plus_format, 
        label="bike"
    )
    assert event3.timestamp == utc_plus_format
    print("   ✅ UTC with +00:00 format works")

    # Test with microseconds
    microsecond_timestamp = base_time.replace(microsecond=123456).isoformat().replace('+00:00', 'Z')
    event4 = QueryEvent(
        camera_id="cam_004",
        timestamp=microsecond_timestamp,
        label="person"
    )
    assert event4.timestamp == microsecond_timestamp
    print("   ✅ Timestamp with microseconds works")

    print("   ✅ All valid timestamp tests passed")


def test_query_event_invalid_timestamps():
    """Test QueryEvent creation with invalid timestamps"""
    print("Testing QueryEvent with invalid timestamps...")

    # Test non-string timestamp
    with pytest.raises(TemporalProcessingError) as exc_info:
        QueryEvent(
            camera_id="cam_001",
            timestamp=1234567890,  # integer instead of string
            label="person"
        )
    assert "timestamp must be a string" in str(exc_info.value)
    print("   ✅ Non-string timestamp rejected")

    # Test missing T separator
    with pytest.raises(TemporalProcessingError) as exc_info:
        QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-13 14:30:00Z",  # space instead of T
            label="person"
        )
    assert "must use 'T' separator" in str(exc_info.value)
    print("   ✅ Missing T separator rejected")

    # Test missing timezone
    with pytest.raises(TemporalProcessingError) as exc_info:
        QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-13T14:30:00",  # no timezone
            label="person"
        )
    assert "timezone information" in str(exc_info.value)
    print("   ✅ Missing timezone rejected")

    # Test invalid datetime format
    with pytest.raises(TemporalProcessingError) as exc_info:
        QueryEvent(
            camera_id="cam_001",
            timestamp="2025-13-32T25:70:00Z",  # invalid date/time
            label="person"
        )
    assert "not a valid ISO 8601 format" in str(exc_info.value)
    print("   ✅ Invalid datetime format rejected")

    # Test future timestamp (more than 1 minute)
    future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    with pytest.raises(TemporalProcessingError) as exc_info:
        QueryEvent(
            camera_id="cam_001",
            timestamp=future_time.isoformat().replace('+00:00', 'Z'),
            label="person"
        )
    assert "cannot be more than 1 minute in the future" in str(exc_info.value)
    print("   ✅ Future timestamp rejected")

    # Test very old timestamp (more than 30 days)
    old_time = datetime.now(timezone.utc) - timedelta(days=31)
    with pytest.raises(TemporalProcessingError) as exc_info:
        QueryEvent(
            camera_id="cam_001",
            timestamp=old_time.isoformat().replace('+00:00', 'Z'),
            label="person"
        )
    assert "too old" in str(exc_info.value)
    print("   ✅ Old timestamp rejected")

    print("   ✅ All invalid timestamp tests passed")


def test_query_event_parsed_timestamp_property():
    """Test the parsed_timestamp property"""
    print("Testing QueryEvent parsed_timestamp property...")

    # Use recent past time to avoid validation issues
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    timestamp_str = base_time.isoformat().replace('+00:00', 'Z')
    
    # Test with Z suffix
    event = QueryEvent(
        camera_id="cam_001",
        timestamp=timestamp_str,
        label="person"
    )
    
    parsed = event.parsed_timestamp
    assert isinstance(parsed, datetime)
    assert parsed.year == base_time.year
    assert parsed.month == base_time.month
    assert parsed.day == base_time.day
    assert parsed.hour == base_time.hour
    assert parsed.minute == base_time.minute
    print("   ✅ Parsed timestamp property works correctly")

    # Test timezone handling
    offset_time = base_time.replace(tzinfo=timezone(timedelta(hours=2)))
    offset_timestamp = offset_time.isoformat()
    event_with_offset = QueryEvent(
        camera_id="cam_002",
        timestamp=offset_timestamp,
        label="vehicle"
    )
    
    parsed_offset = event_with_offset.parsed_timestamp
    assert parsed_offset.tzinfo is not None
    print("   ✅ Timezone information preserved")

    print("   ✅ Parsed timestamp property tests passed")


def test_query_event_is_recent_method():
    """Test the is_recent method"""
    print("Testing QueryEvent is_recent method...")

    # Test recent timestamp (within default 60 minutes)
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    recent_event = QueryEvent(
        camera_id="cam_001",
        timestamp=recent_time.isoformat().replace('+00:00', 'Z'),
        label="person"
    )
    
    assert recent_event.is_recent() == True
    print("   ✅ Recent timestamp identified correctly")

    # Test old timestamp (beyond default 60 minutes)
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    old_event = QueryEvent(
        camera_id="cam_002",
        timestamp=old_time.isoformat().replace('+00:00', 'Z'),
        label="vehicle"
    )
    
    assert old_event.is_recent() == False
    print("   ✅ Old timestamp identified correctly")

    # Test custom max_age
    somewhat_old_time = datetime.now(timezone.utc) - timedelta(minutes=90)
    somewhat_old_event = QueryEvent(
        camera_id="cam_003",
        timestamp=somewhat_old_time.isoformat().replace('+00:00', 'Z'),
        label="bike"
    )
    
    assert somewhat_old_event.is_recent(max_age_minutes=120) == True
    assert somewhat_old_event.is_recent(max_age_minutes=60) == False
    print("   ✅ Custom max_age parameter works")

    print("   ✅ is_recent method tests passed")


def test_query_event_with_bbox():
    """Test QueryEvent with optional bbox parameter"""
    print("Testing QueryEvent with bbox...")

    # Use recent past time to avoid validation issues
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    timestamp_str = base_time.isoformat().replace('+00:00', 'Z')

    bbox_data = {"x": 100, "y": 200, "width": 50, "height": 75}
    event = QueryEvent(
        camera_id="cam_001",
        timestamp=timestamp_str,
        label="person",
        bbox=bbox_data
    )
    
    assert event.bbox == bbox_data
    assert event.camera_id == "cam_001"
    print("   ✅ QueryEvent with bbox works correctly")

    # Test without bbox (should default to None)
    event_no_bbox = QueryEvent(
        camera_id="cam_002",
        timestamp=timestamp_str,
        label="vehicle"
    )
    
    assert event_no_bbox.bbox is None
    print("   ✅ QueryEvent without bbox defaults to None")

    print("   ✅ Bbox parameter tests passed")


if __name__ == "__main__":
    """Run all tests if script is executed directly"""
    test_query_event_valid_timestamps()
    test_query_event_invalid_timestamps()
    test_query_event_parsed_timestamp_property()
    test_query_event_is_recent_method()
    test_query_event_with_bbox()
    
    print("\n🎉 All QueryEvent timestamp validation tests passed!")
    print("✅ Enhanced timestamp validation is working correctly in the domain model")
