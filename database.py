import sqlite3

DB_NAME = "village.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS npc_affinity (
            npc_id TEXT PRIMARY KEY,
            affinity INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("✅ 데이터베이스 창고 준비 완료!")


# 👇 [새로 추가된 기능 1] 창고에서 현재 호감도 읽어오기
def get_npc_affinity(npc_id: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT affinity FROM npc_affinity WHERE npc_id = ?", (npc_id,))
    result = cursor.fetchone()
    conn.close()

    # 창고에 기록이 없다면? (처음 대화하는 NPC인 경우) -> 기본값 0점 반환!
    if result is None:
        return 0
    else:
        return result[0]


# 👇 [새로 추가된 기능 2] 창고에 새로운 호감도 저장/덮어쓰기
def update_npc_affinity(npc_id: str, new_affinity: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # INSERT OR REPLACE: 기존 기록이 없으면 '새로 추가(INSERT)', 있으면 '덮어쓰기(REPLACE)' 해주는 아주 꿀 같은 쿼리입니다!
    cursor.execute("""
        INSERT OR REPLACE INTO npc_affinity (npc_id, affinity)
        VALUES (?, ?)
    """, (npc_id, new_affinity))

    conn.commit()
    conn.close()


# 테스트용 코드 (직접 실행했을 때만 작동)
if __name__ == "__main__":
    init_db()

    # 💡 잘 작동하는지 테스트해 봅시다!
    update_npc_affinity("cheese", 15)  # 치즈 호감도를 15로 저장해보기
    saved_score = get_npc_affinity("cheese")  # 치즈 호감도 다시 꺼내보기
    print(f"테스트 결과: 현재 치즈의 창고 속 호감도는 {saved_score}점 입니다!")