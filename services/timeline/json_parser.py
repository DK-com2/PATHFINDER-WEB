"""
JSON Parser Module
Android/iPhone形式の判別とデータ構造の解析
"""

from typing import Dict, List, Union, Optional, Iterator, IO
import logging
import ijson
from .config import DEBUG
from .validator import TimelineDataValidator
from .converter import TimelineDataConverter

logger = logging.getLogger(__name__)


class TimelineJSONParser:
    """Google Timeline JSONデータの解析クラス"""
    
    def __init__(self):
        self.validator = TimelineDataValidator()
        self.converter = TimelineDataConverter()
    
    def parse_json_data(self, data: Union[Dict, List], username: str) -> List[Dict]:
        """JSONデータを解析（既存の後方互換性のため）"""
        try:
            data_format = self.validator.detect_format(data)
            if DEBUG:
                logger.info(f"データ形式: {data_format.upper()}")
            
            if not self.validator.validate_json_structure(data, data_format):
                raise ValueError("データ構造の検証に失敗しました")
            
            if data_format == "android":
                records = []
                for segment in data['semanticSegments']:
                    records.extend(self.process_android_segment(segment, username))
                return records
            elif data_format == "iphone":
                records = []
                for item in data:
                    records.extend(self.process_iphone_item(item, username))
                return records
            else:
                raise ValueError(f"未対応の形式: {data_format}")
                
        except Exception as e:
            if DEBUG:
                logger.error(f"データ解析エラー: {e}")
            return []

    def parse_json_stream(self, file_obj: IO, username: str) -> Iterator[Dict]:
        """ストリームからJSONデータを解析してレコードをジェネレートする"""
        try:
            # ijson.parseを使用して最初のイベントを取得し、形式を判定する
            # ただし、ストリームの位置を戻す必要がある
            # SpooledTemporaryFileなら seek(0) が可能と想定

            format_type = "unknown"
            parser = ijson.parse(file_obj)
            for prefix, event, value in parser:
                if (prefix, event) == ('', 'start_map'):
                    # Object start -> Android or unexpected object
                    format_type = "android"
                    break
                elif (prefix, event) == ('', 'start_array'):
                    # Array start -> iPhone or unexpected array
                    format_type = "iphone"
                    break

            # ストリームをリセット
            if file_obj.seekable():
                file_obj.seek(0)
            else:
                raise ValueError("Stream is not seekable")

            if format_type == "android":
                # Android format: root object -> semanticSegments array -> items
                items = ijson.items(file_obj, 'semanticSegments.item')
                for item in items:
                    for record in self.process_android_segment(item, username):
                        yield record
            elif format_type == "iphone":
                # iPhone format: root array -> items
                items = ijson.items(file_obj, 'item')
                for item in items:
                    for record in self.process_iphone_item(item, username):
                        yield record
            else:
                 # Default fallback or error if unknown structure
                 logger.warning("Unknown JSON structure start, trying generic parsing")
                 pass

        except Exception as e:
            logger.error(f"ストリーム解析エラー: {e}")
            raise

    def process_android_segment(self, segment: Dict, username: str) -> List[Dict]:
        """Android形式の1セグメントを処理"""
        records = []
        start_time = segment.get('startTime')
        end_time = segment.get('endTime')
        
        # timelinePath処理
        if 'timelinePath' in segment:
            for path in segment['timelinePath']:
                point_time = path.get('time')

                # Android形式の座標解析
                lat, lng = self.converter.parse_android_coordinates(path.get('point', ''))

                record = {
                    "type": "timelinePath",
                    "start_time": start_time,
                    "end_time": end_time,
                    "point_time": point_time,
                    "latitude": lat,
                    "longitude": lng,
                    "visit_probability": None,
                    "visit_placeId": None,
                    "visit_semanticType": None,
                    "activity_distanceMeters": None,
                    "activity_type": None,
                    "activity_probability": None,
                    "username": username,
                    "_gpx_data_source": None,
                    "_gpx_track_name": None,
                    "_gpx_elevation": None,
                    "_gpx_speed": None,
                    "_gpx_point_sequence": None
                }

                # データ正規化
                normalized_record = self.converter.normalize_record(record)

                if self.validator.validate_record(normalized_record):
                    records.append(normalized_record)

        # visit処理
        if 'visit' in segment:
            visit = segment['visit']
            top_candidate = visit.get('topCandidate', {})
            place_location = top_candidate.get('placeLocation', {})
            
            # Android形式の座標解析
            lat, lng = self.converter.parse_android_coordinates(
                place_location.get('latLng', '')
            )

            record = {
                "type": "visit",
                "start_time": start_time,
                "end_time": end_time,
                "point_time": None,
                "latitude": lat,
                "longitude": lng,
                "visit_probability": visit.get('probability'),
                "visit_placeId": top_candidate.get('placeId'),
                "visit_semanticType": top_candidate.get('semanticType'),
                "activity_distanceMeters": None,
                "activity_type": None,
                "activity_probability": None,
                "username": username,
                "_gpx_data_source": None,
                "_gpx_track_name": None,
                "_gpx_elevation": None,
                "_gpx_speed": None,
                "_gpx_point_sequence": None
            }

            # データ正規化
            normalized_record = self.converter.normalize_record(record)

            if self.validator.validate_record(normalized_record):
                records.append(normalized_record)

        # activity処理
        if 'activity' in segment:
            activity = segment['activity']
            top_candidate = activity.get('topCandidate', {})

            for key in ['start', 'end']:
                if key in activity and 'latLng' in activity[key]:
                    # Android形式の座標解析
                    lat, lng = self.converter.parse_android_coordinates(
                        activity[key]['latLng']
                    )
                    
                    record = {
                        "type": f"activity_{key}",
                        "start_time": start_time,
                        "end_time": end_time,
                        "point_time": None,
                        "latitude": lat,
                        "longitude": lng,
                        "visit_probability": None,
                        "visit_placeId": None,
                        "visit_semanticType": None,
                        "activity_distanceMeters": activity.get('distanceMeters'),
                        "activity_type": top_candidate.get('type'),
                        "activity_probability": top_candidate.get('probability'),
                        "username": username,
                        "_gpx_data_source": None,
                        "_gpx_track_name": None,
                        "_gpx_elevation": None,
                        "_gpx_speed": None,
                        "_gpx_point_sequence": None
                    }
                    
                    # データ正規化
                    normalized_record = self.converter.normalize_record(record)
                    
                    if self.validator.validate_record(normalized_record):
                        records.append(normalized_record)
        return records

    def process_iphone_item(self, segment: Dict, username: str) -> List[Dict]:
        """iPhone形式の1アイテムを処理"""
        records = []
        start_time = segment.get('startTime')
        end_time = segment.get('endTime')

        # Visit情報の処理
        if 'visit' in segment:
            visit = segment['visit']
            top_candidate = visit.get('topCandidate', {})
            place_location = top_candidate.get('placeLocation', '')
            
            # iPhone形式の座標解析
            lat, lng = self.converter.extract_geo_coordinates(place_location)

            record = {
                "type": "visit",
                "start_time": start_time,
                "end_time": end_time,
                "point_time": None,
                "latitude": lat,
                "longitude": lng,
                "visit_probability": visit.get('probability'),
                "visit_placeId": top_candidate.get('placeID'),
                "visit_semanticType": top_candidate.get('semanticType'),
                "activity_distanceMeters": None,
                "activity_type": None,
                "activity_probability": None,
                "username": username,
                "_gpx_data_source": None,
                "_gpx_track_name": None,
                "_gpx_elevation": None,
                "_gpx_speed": None,
                "_gpx_point_sequence": None
            }

            # データ正規化
            normalized_record = self.converter.normalize_record(record)

            if self.validator.validate_record(normalized_record):
                records.append(normalized_record)

        # Activity情報の処理
        if 'activity' in segment:
            activity = segment['activity']
            top_candidate = activity.get('topCandidate', {})

            # 開始位置
            start_lat, start_lng = self.converter.extract_geo_coordinates(
                activity.get('start', '')
            )
            if start_lat and start_lng:
                record = {
                    "type": "activity_start",
                    "start_time": start_time,
                    "end_time": end_time,
                    "point_time": None,
                    "latitude": start_lat,
                    "longitude": start_lng,
                    "visit_probability": None,
                    "visit_placeId": None,
                    "visit_semanticType": None,
                    "activity_distanceMeters": activity.get('distanceMeters'),
                    "activity_type": top_candidate.get('type'),
                    "activity_probability": top_candidate.get('probability'),
                    "username": username,
                    "_gpx_data_source": None,
                    "_gpx_track_name": None,
                    "_gpx_elevation": None,
                    "_gpx_speed": None,
                    "_gpx_point_sequence": None
                }
                
                # データ正規化
                normalized_record = self.converter.normalize_record(record)
                
                if self.validator.validate_record(normalized_record):
                    records.append(normalized_record)
            
            # 終了位置
            end_lat, end_lng = self.converter.extract_geo_coordinates(
                activity.get('end', '')
            )
            if end_lat and end_lng:
                record = {
                    "type": "activity_end",
                    "start_time": start_time,
                    "end_time": end_time,
                    "point_time": None,
                    "latitude": end_lat,
                    "longitude": end_lng,
                    "visit_probability": None,
                    "visit_placeId": None,
                    "visit_semanticType": None,
                    "activity_distanceMeters": activity.get('distanceMeters'),
                    "activity_type": top_candidate.get('type'),
                    "activity_probability": top_candidate.get('probability'),
                    "username": username,
                    "_gpx_data_source": None,
                    "_gpx_track_name": None,
                    "_gpx_elevation": None,
                    "_gpx_speed": None,
                    "_gpx_point_sequence": None
                }
                
                # データ正規化
                normalized_record = self.converter.normalize_record(record)
                
                if self.validator.validate_record(normalized_record):
                    records.append(normalized_record)
        
        return records

    def get_parsing_summary(self) -> Dict:
        """解析結果のサマリーを取得"""
        return self.validator.get_validation_summary()