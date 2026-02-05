import sys
import os
import json
import tempfile
from io import BytesIO

# Add repo root to sys.path
sys.path.append(os.getcwd())

from services.timeline.json_parser import TimelineJSONParser

def test_android_stream():
    print("Testing Android Stream...")
    android_data = {
        "semanticSegments": [
            {
                "startTime": "2023-01-01T00:00:00Z",
                "endTime": "2023-01-01T01:00:00Z",
                "visit": {
                    "topCandidate": {
                        "placeId": "test_place",
                        "placeLocation": {"latLng": "45.0, 90.0"}
                    }
                }
            }
        ]
    }

    json_bytes = json.dumps(android_data).encode('utf-8')
    f = BytesIO(json_bytes)

    parser = TimelineJSONParser()
    records = list(parser.parse_json_stream(f, "test_user"))

    assert len(records) == 1
    assert records[0]['type'] == 'visit'
    assert records[0]['username'] == 'test_user'
    print("Android Stream Test Passed!")

def test_iphone_stream():
    print("Testing iPhone Stream...")
    iphone_data = [
        {
            "startTime": "2023-01-01T00:00:00Z",
            "endTime": "2023-01-01T01:00:00Z",
            "visit": {
                "topCandidate": {
                    "placeID": "test_place_iphone",
                    "placeLocation": "GeoCoordinates: 45.0, 90.0"
                }
            }
        }
    ]

    json_bytes = json.dumps(iphone_data).encode('utf-8')
    f = BytesIO(json_bytes)

    parser = TimelineJSONParser()
    records = list(parser.parse_json_stream(f, "test_user"))

    assert len(records) == 1
    assert records[0]['type'] == 'visit'
    assert records[0]['username'] == 'test_user'
    print("iPhone Stream Test Passed!")

if __name__ == "__main__":
    test_android_stream()
    test_iphone_stream()
