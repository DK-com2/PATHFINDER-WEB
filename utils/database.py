import psycopg2
import os
from typing import Optional
import logging
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """PostgreSQL データベースへの接続を取得"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def test_db_connection():
    """データベース接続のテスト"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def init_db():
    """データベースの初期化とマイグレーションを実行"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # PostGIS 拡張機能の有効化
        logger.info("Checking PostGIS extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        # geom カラムの追加（存在しない場合）
        logger.info("Migrating schema...")
        
        # テーブル作成（存在しない場合）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS timeline_data (
                id SERIAL PRIMARY KEY,
                type VARCHAR(50),
                start_time TIMESTAMP WITH TIME ZONE,
                end_time TIMESTAMP WITH TIME ZONE,
                point_time TIMESTAMP WITH TIME ZONE,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                visit_probability DOUBLE PRECISION,
                visit_placeid TEXT,
                visit_semantictype TEXT,
                activity_distancemeters DOUBLE PRECISION,
                activity_type TEXT,
                activity_probability DOUBLE PRECISION,
                username TEXT,
                _gpx_data_source TEXT,
                _gpx_track_name TEXT,
                _gpx_elevation DOUBLE PRECISION,
                _gpx_speed DOUBLE PRECISION,
                _gpx_point_sequence INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # フォローテーブル作成（存在しない場合）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS follows (
                follower_username TEXT NOT NULL,
                followed_username TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (follower_username, followed_username)
            );
        """)

        cur.execute("""
            DO $$ 
            BEGIN 
                -- geom カラムの追加
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='timeline_data' AND column_name='geom') THEN
                    ALTER TABLE timeline_data ADD COLUMN geom geometry(Point, 4326);
                    RAISE NOTICE 'Added geom column';
                END IF;

                -- インデックスの作成
                IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                             WHERE tablename='timeline_data' AND indexname='idx_timeline_geom') THEN
                    CREATE INDEX idx_timeline_geom ON timeline_data USING GIST (geom);
                    RAISE NOTICE 'Created GIST index on geom';
                END IF;
                
                -- 通常のカラムへのインデックス
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname='idx_timeline_username_time') THEN
                    CREATE INDEX idx_timeline_username_time ON timeline_data (username, start_time DESC);
                END IF;
            END $$;
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialization completed successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False