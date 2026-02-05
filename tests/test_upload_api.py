import sys
from unittest.mock import MagicMock

# supabaseモジュールをモック化 (main.pyのインポート前に実行)
mock_supabase_module = MagicMock()
sys.modules["supabase"] = mock_supabase_module

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json
import io
import os

# 環境変数の設定
os.environ['DATABASE_URL'] = 'postgres://user:pass@localhost/db'
os.environ['SUPABASE_URL'] = 'http://test'
os.environ['SUPABASE_KEY'] = 'test_key'
os.environ['SECRET_KEY'] = 'test_secret'

# main.pyのインポート
from main import app
from api.auth import get_current_user

client = TestClient(app)

# 認証のモック
async def mock_get_current_user():
    return {"user_id": "test_user_id"}

app.dependency_overrides[get_current_user] = mock_get_current_user

# DB接続のモック
@pytest.fixture
def mock_db_connection():
    with patch('api.timeline.upload.get_db_connection') as mock_conn1, \
         patch('api.timeline.fast_upload.get_db_connection') as mock_conn2:
        mock_cursor = MagicMock()
        mock_conn1.return_value.cursor.return_value = mock_cursor
        mock_conn2.return_value.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1000
        yield mock_conn1

# Supabaseのモック
@pytest.fixture(autouse=True)
def setup_supabase_mock():
    mock_client_instance = MagicMock()
    mock_supabase_module.create_client.return_value = mock_client_instance

    # usernameレスポンスのモック
    mock_response = MagicMock()
    mock_response.data = [{"username": "test_user"}]
    mock_client_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    return mock_client_instance

def test_upload_streaming(mock_db_connection):
    # ダミーのJSONファイル作成 (バッチサイズ1000を超えるデータ量)
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
        ] * 1500
    }

    json_content = json.dumps(android_data).encode('utf-8')
    files = {'file': ('test.json', io.BytesIO(json_content), 'application/json')}

    response = client.post("/api/timeline/upload", files=files)

    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['total_records'] == 1500

    mock_cursor = mock_db_connection.return_value.cursor.return_value
    assert mock_cursor.copy_expert.call_count == 2

def test_fast_upload_streaming(mock_db_connection):
    # ダミーのJSONファイル作成
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
        ] * 1500
    }

    json_content = json.dumps(android_data).encode('utf-8')
    files = {'file': ('test.json', io.BytesIO(json_content), 'application/json')}

    response = client.post("/api/timeline/fast-upload", files=files)

    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['total_records'] == 1500

    mock_cursor = mock_db_connection.return_value.cursor.return_value
    # test_upload_streaming で2回呼ばれているので、累積で4回になるはず
    # あるいは mock_cursor.reset_mock() を呼び出したいところだが、
    # fixtureがfunctionスコープなら毎回作り直されるはず。
    # しかし、mock_cursor は fixture の内部で作られた MagicMock で、
    # mock_db_connection (mock_conn1) の戻り値としてセットされている。
    # function scope なら fixture 全体が再実行され、新しい MagicMock が作られるはず。
    assert mock_cursor.copy_expert.call_count == 2
