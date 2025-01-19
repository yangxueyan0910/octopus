import os
import sqlite3
import sys
import sqlite_queue

from threading import Lock
BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
# 数据库连接
def connect():
    print(BASE_DIR + "\live_info.db")
    conn = sqlite3.connect(BASE_DIR + "\live_info.db", check_same_thread=False)
    cursor = conn.cursor()
    lock_main = Lock()

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS "live_list_info" (
                "platform"	TEXT NOT NULL,
                "room_id"	TEXT NOT NULL,
                "name"	TEXT,
                "live_status"	TEXT,
                "save_dir"	TEXT,
                "flag"	TEXT,
                PRIMARY KEY("platform","room_id")
            )
            """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "download_video_list" (
        "video_url" TEXT NOT NULL,
        "bvid" TEXT NOT NULL,
        "video_title" TEXT,
        "finish_flag" INTEGER,
        "save_path" TEXT,
        PRIMARY KEY("video_url")
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "live_setting" (
            "id"	INTEGER NOT NULL,
            "name"	TEXT NOT NULL,
            "resolution"	TEXT,
            "code_rate"	TEXT,
            "frame_rate"	TEXT,
            "path"	TEXT,
            "flag"	INTEGER NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        );
    """)

    return cursor, conn, lock_main
