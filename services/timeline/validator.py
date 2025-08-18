"""
Data Validator Module
タイムラインデータの検証とクリーニング機能
"""

from typing import Dict, List, Union, Optional
from datetime import datetime
import logging
from .config import VALIDATION_CONFIG, ERROR_CONFIG, DETECTION_PATTERNS, DEBUG

logger = logging.getLogger(__name__)


class TimelineDataValidator:
    """タイムラインデータの検証クラス"""
    
    def __init__(self, strict_mode: Optional[bool] = None):
        self.strict_mode = strict_mode if strict_mode is not None else ERROR_CONFIG["strict_mode"]
        self.validation_config = VALIDATION_CONFIG
        self.errors = []
        self.warnings = []
    
    def detect_format(self, data: Union[Dict, List]) -> str:
        """データ形式を自動検出"""
        try:
            # iPhone形式の検出
            if isinstance(data, list) and len(data) > 0:
                if all(isinstance(item, dict) for item in data[:3]):  # 最初の3項目をチェック
                    first_item = data[0]
                    if 'startTime' in first_item:
                        return "iphone"
            
            # Android形式の検出
            if isinstance(data, dict):
                if 'semanticSegments' in data:
                    return "android"
            
            raise ValueError("未対応のデータ形式です")
            
        except Exception as e:
            self._add_error(f"データ形式検出エラー: {e}")
            raise
    
    def validate_json_structure(self, data: Union[Dict, List], expected_format: str) -> bool:
        """JSONデータ構造の検証"""
        try:
            pattern = DETECTION_PATTERNS.get(expected_format)
            if not pattern:
                raise ValueError(f"未対応の形式: {expected_format}")
            
            if expected_format == "android":
                return self._validate_android_structure(data, pattern)
            elif expected_format == "iphone":
                return self._validate_iphone_structure(data, pattern)
            
        except Exception as e:
            self._add_error(f"構造検証エラー: {e}")
            return False
    
    def _validate_android_structure(self, data: Dict, pattern: Dict) -> bool:
        """Android形式の構造検証"""
        if not isinstance(data, dict):
            self._add_error("Android形式はdict型である必要があります")
            return False
        
        # 必須フィールドの確認
        for field in pattern["required_fields"]:
            if field not in data:
                self._add_error(f"必須フィールドが不足: {field}")
                return False
        
        # semanticSegmentsの中身を検証
        segments = data.get("semanticSegments", [])
        if not isinstance(segments, list):
            self._add_error("semanticSegmentsはlist型である必要があります")
            return False
        
        if len(segments) == 0:
            self._add_warning("semanticSegmentsが空です")
        
        return True
    
    def _validate_iphone_structure(self, data: List, pattern: Dict) -> bool:
        """iPhone形式の構造検証"""
        if not isinstance(data, list):
            self._add_error("iPhone形式はlist型である必要があります")
            return False
        
        if len(data) == 0:
            self._add_warning("データが空です")
            return True
        
        # 最初の要素を検証
        first_item = data[0]
        if not isinstance(first_item, dict):
            self._add_error("各要素はdict型である必要があります")
            return False
        
        # 必須フィールドの確認
        for field in pattern["required_fields"]:
            if field not in first_item:
                self._add_error(f"必須フィールドが不足: {field}")
                return False
        
        return True
    
    def validate_coordinates(self, lat: float, lng: float) -> bool:
        """座標データの検証"""
        if lat is None or lng is None:
            return True  # None は許可
        
        try:
            lat, lng = float(lat), float(lng)
            
            if not (self.validation_config["min_latitude"] <= lat <= self.validation_config["max_latitude"]):
                self._add_warning(f"緯度が範囲外: {lat}")
                return False
            
            if not (self.validation_config["min_longitude"] <= lng <= self.validation_config["max_longitude"]):
                self._add_warning(f"経度が範囲外: {lng}")
                return False
            
            return True
            
        except (ValueError, TypeError):
            self._add_warning(f"座標の変換エラー: lat={lat}, lng={lng}")
            return False
    
    def validate_probability(self, prob: float) -> bool:
        """確率値の検証"""
        if prob is None:
            return True
        
        try:
            prob = float(prob)
            if not (self.validation_config["min_probability"] <= prob <= self.validation_config["max_probability"]):
                self._add_warning(f"確率値が範囲外: {prob}")
                return False
            return True
            
        except (ValueError, TypeError):
            self._add_warning(f"確率値の変換エラー: {prob}")
            return False
    
    def validate_distance(self, distance: float) -> bool:
        """距離データの検証"""
        if distance is None:
            return True
        
        try:
            distance = float(distance)
            if distance < 0:
                self._add_warning(f"距離は負の値にできません: {distance}")
                return False
            
            if distance > self.validation_config["max_distance_meters"]:
                self._add_warning(f"距離が上限を超えています: {distance}")
                return False
            
            return True
            
        except (ValueError, TypeError):
            self._add_warning(f"距離の変換エラー: {distance}")
            return False
    
    def validate_timestamp(self, timestamp_str: str) -> bool:
        """タイムスタンプの検証"""
        if not timestamp_str:
            return True
        
        try:
            # ISO形式での解析を試行
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return True
            
        except Exception:
            self._add_warning(f"タイムスタンプ解析エラー: {timestamp_str}")
            return False
    
    def validate_record(self, record: Dict) -> bool:
        """レコード全体の検証"""
        is_valid = True
        
        # 座標検証
        lat, lng = record.get('latitude'), record.get('longitude')
        if lat is not None or lng is not None:
            if not self.validate_coordinates(lat, lng):
                is_valid = False
        
        # 確率値検証
        for prob_field in ['visit_probability', 'activity_probability']:
            if prob_field in record:
                if not self.validate_probability(record[prob_field]):
                    is_valid = False
        
        # 距離検証
        if 'activity_distanceMeters' in record:
            if not self.validate_distance(record['activity_distanceMeters']):
                is_valid = False
        
        # タイムスタンプ検証
        for time_field in ['start_time', 'end_time', 'point_time']:
            if time_field in record and record[time_field]:
                if not self.validate_timestamp(record[time_field]):
                    is_valid = False
        
        return is_valid
    
    def _add_error(self, message: str):
        """エラーメッセージを追加"""
        self.errors.append(message)
        if DEBUG:
            logger.error(f"エラー: {message}")
    
    def _add_warning(self, message: str):
        """警告メッセージを追加"""
        self.warnings.append(message)
        if DEBUG:
            logger.warning(f"警告: {message}")
    
    def get_validation_summary(self) -> Dict:
        """検証結果のサマリーを取得"""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "is_valid": len(self.errors) == 0
        }
    
    def reset(self):
        """エラー・警告をリセット"""
        self.errors = []
        self.warnings = []