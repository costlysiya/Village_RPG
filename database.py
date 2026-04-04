import sqlite3

DB_NAME = "village.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. 기존: 호감도 저장 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS npc_affinity (
            npc_id TEXT PRIMARY KEY,
            affinity INTEGER NOT NULL
        )
    """)

    # 👇 [새로 추가!] 2. 대화 기록을 저장할 '기억력' 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id TEXT NOT NULL,
            speaker TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)

    # 3. 마을에 설치된 물건들(건물, 꽃 등)의 위치를 저장할 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS village_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_name TEXT NOT NULL,
            pos_x REAL NOT NULL,
            pos_y REAL NOT NULL,
            pos_z REAL NOT NULL
        )
    """)

    # 4. [새로 추가] NPC별 퀘스트(의뢰) 진행 상태를 저장하는 테이블
    # 한 NPC당 하나의 의뢰만 진행한다고 가정하고 npc_id를 고유키(PRIMARY KEY)로 씁니다.
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS quest_status (
                npc_id TEXT PRIMARY KEY,
                quest_name TEXT NOT NULL,
                status TEXT NOT NULL,
                completion_time REAL NOT NULL
            )
        """)

    # 5. [새로 추가] 플레이어의 인벤토리(가방) 테이블
    # 아이템 이름을 고유키로 써서, 똑같은 아이템을 얻으면 수량(quantity)만 늘어나게 합니다.
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                item_name TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL DEFAULT 0
            )
        """)

    conn.commit()
    conn.close()
    print("✅ 데이터베이스 창고 준비 완료! (objects 추가됨)")


# --- (기존 호감도 함수들 그대로 유지) ---
def get_npc_affinity(npc_id: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT affinity FROM npc_affinity WHERE npc_id = ?", (npc_id,))
    result = cursor.fetchone()
    conn.close()
    return 0 if result is None else result[0]


def update_npc_affinity(npc_id: str, new_affinity: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO npc_affinity (npc_id, affinity)
        VALUES (?, ?)
    """, (npc_id, new_affinity))
    conn.commit()
    conn.close()


# 👇 [새로 추가된 기능 1] 대화 내용을 창고에 한 줄 적는 함수
def save_chat_message(npc_id: str, speaker: str, message: str):
    # speaker 자리에는 'player' 또는 'npc' 라는 글자가 들어갈 겁니다.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (npc_id, speaker, message)
        VALUES (?, ?, ?)
    """, (npc_id, speaker, message))
    conn.commit()
    conn.close()


# 👇 [새로 추가된 기능 2] AI에게 알려주기 위해 최근 대화 N개를 꺼내오는 함수
def get_recent_chat_history(npc_id: str, limit: int = 5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 가장 최근 대화부터 가져오기 위해 순서를 거꾸로(DESC) 해서 몇 개(limit)만 가져옵니다.
    cursor.execute("""
        SELECT speaker, message 
        FROM chat_history 
        WHERE npc_id = ? 
        ORDER BY id DESC 
        LIMIT ?
    """, (npc_id, limit))

    results = cursor.fetchall()
    conn.close()

    # 과거 -> 현재 시간 순서대로 AI에게 읽혀야 하므로 리스트를 다시 뒤집어줍니다.
    results.reverse()
    return results


# 👇 [건물 기능 1] 새로운 물건을 마을에 배치할 때 쓰는 함수
def place_object(object_name: str, x: float, y: float, z: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO village_objects (object_name, pos_x, pos_y, pos_z)
        VALUES (?, ?, ?, ?)
    """, (object_name, x, y, z))
    conn.commit()
    conn.close()


# 👇 [건물 기능 2] 유니티가 켜질 때 마을의 모든 물건 위치를 싹 다 가져가는 함수
def get_all_objects():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT object_name, pos_x, pos_y, pos_z FROM village_objects")
    results = cursor.fetchall()
    conn.close()

    # 딕셔너리(JSON) 형태로 예쁘게 포장해서 돌려줍니다.
    objects_list = []
    for row in results:
        objects_list.append({
            "object_name": row[0],
            "x": row[1],
            "y": row[2],
            "z": row[3]
        })
    return objects_list


# ==========================================
# [퀘스트 관련 기능]
# ==========================================
def save_quest_status(npc_id: str, quest_name: str, status: str, completion_time: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 의뢰를 새로 받거나 상태가 바뀔 때 덮어씌웁니다.
    cursor.execute("""
        INSERT OR REPLACE INTO quest_status (npc_id, quest_name, status, completion_time)
        VALUES (?, ?, ?, ?)
    """, (npc_id, quest_name, status, completion_time))
    conn.commit()
    conn.close()


def get_quest_status(npc_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quest_name, status, completion_time FROM quest_status WHERE npc_id = ?", (npc_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"quest_name": result[0], "status": result[1], "completion_time": result[2]}
    return None


def delete_quest(npc_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 퀘스트 완료 후 보상을 받고 나면 장부에서 지워버립니다.
    cursor.execute("DELETE FROM quest_status WHERE npc_id = ?", (npc_id,))
    conn.commit()
    conn.close()


# ==========================================
# [인벤토리 관련 기능]
# ==========================================
def add_inventory_item(item_name: str, amount: int = 1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 이미 있는 아이템이면 개수만 더하고(+amount), 처음 얻는 거면 새로 기록합니다.
    cursor.execute("""
        INSERT INTO inventory (item_name, quantity) 
        VALUES (?, ?)
        ON CONFLICT(item_name) DO UPDATE SET quantity = quantity + ?
    """, (item_name, amount, amount))
    conn.commit()
    conn.close()

# 테스트용 코드 (직접 실행했을 때만 작동)
if __name__ == "__main__":
    init_db()
