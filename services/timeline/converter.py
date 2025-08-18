"""
Data Converter Module
時間変換、座標データの統一、データ型の正規化
"""

from typing import List, Dict, Union, Optional, Tuple
from datetime import datetime, timezone
import pytz
import logging
from .config import INPUT_TIMEZONE, OUTPUT_TIMEZONE, DEBUG

logger = logging.getLogger(__name__)


class TimelineDataConverter:
    """タイムラインデータの変換クラス"""
    
    def __init__(self):
        self.input_timezone = INPUT_TIMEZONE
        self.output_timezone = OUTPUT_TIMEZONE
    
    def convert_timestamp_to_utc(self, timestamp_str: str) -> Optional[datetime]:
        """タイムスタンプ文字列をUTCに変換"""
        if not timestamp_str:
            return None
        
        try:
            # ISO形式で解析
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # タイムゾーン処理
            if dt.tzinfo is None:
                # タイムゾーン情報がない場合は日本時間として解釈
                jst = pytz.timezone(self.input_timezone)
                dt = jst.localize(dt)
            
            # UTCに変換
            return dt.astimezone(pytz.UTC)
            
        except Exception as e:
            if DEBUG:
                logger.warning(f"時間変換エラー: {timestamp_str} -> {e}")
            return None
    
    def normalize_numeric_value(self, value) -> Optional[float]:
        """数値データの正規化"""
        if value is None or value == '':
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def extract_geo_coordinates(self, geo_str: str) -> Tuple[Optional[float], Optional[float]]:
        """geo:35.639772,139.670222 のような形式から緯度経度を抽出"""
        if not geo_str or not isinstance(geo_str, str):
            return None, None
        
        try:
            # iPhone形式: "geo:35.639772,139.670222"
            parts = geo_str.replace('geo:', '').split(',')
            if len(parts) >= 2:
                return float(parts[0]), float(parts[1])
        except Exception:
            pass
        
        return None, None
    
    def parse_android_coordinates(self, coord_str: str) -> Tuple[Optional[float], Optional[float]]:
        """Android形式の座標文字列を解析"""
        if not coord_str or not isinstance(coord_str, str):
            return None, None
        
        try:
            # Android形式: "35.639772°, 139.670222°"
            lat, lng = map(float, coord_str.replace('°', '').split(', '))
            return lat, lng
        except Exception:
            return None, None
    
    def normalize_record(self, record: Dict) -> Dict:
        """レコードの正規化（時間変換と数値変換）"""
        normalized = record.copy()
        
        # 時間カラムの変換
        time_columns = ['start_time', 'end_time', 'point_time']
        for col in time_columns:
            if col in normalized and normalized[col]:
                converted_time = self.convert_timestamp_to_utc(str(normalized[col]))
                normalized[col] = converted_time.isoformat() if converted_time else None
        
        # 数値カラムの変換
        numeric_columns = [
            'latitude', 'longitude', 'activity_distanceMeters', 
            'visit_probability', 'activity_probability',
            '_gpx_elevation', '_gpx_speed', '_gpx_point_sequence'
        ]
        
        for col in numeric_columns:
            if col in normalized:
                normalized[col] = self.normalize_numeric_value(normalized[col])
        
        return normalized