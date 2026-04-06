from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import random
import time # 시간 계산을 위해 추가

from npc_ai import get_npc_response, generate_npc_gossip  # ai함수 가져옴
from database import (  # db 불러옴
    get_npc_affinity, update_npc_affinity, save_chat_message, get_recent_chat_history,
    place_object, get_all_objects, save_npc_gossip,
    save_quest_status, get_quest_status, delete_quest, add_inventory_item
)

app = FastAPI()

# 1. CORS 설정: WebGL 환경에서의 통신 에러(접근 차단) 방지
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST 등 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


# 2. 데이터 규격 정의 (유니티 -> 서버)
class ChatRequest(BaseModel):
    npc_id: str
    player_message: str


# 3. 데이터 규격 정의 (서버 -> 유니티)
class ChatResponse(BaseModel):
    npc_response: str
    intimacy_change: int
    final_affinity: int

# 👇 [새로 추가] 유니티가 건물을 지을 때 서버로 보낼 데이터 양식입니다.
class BuildRequest(BaseModel):
    object_name: str
    x: float
    y: float
    z: float


# 4. 채팅 API 엔드포인트
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_npc(request: ChatRequest):
    print(f"\n[{request.npc_id}에게 온 메시지]: {request.player_message}")

    # 1. 호감도 & 과거 대화 불러오기
    start_affinity = get_npc_affinity(request.npc_id)
    recent_history = get_recent_chat_history(request.npc_id, limit=5)

    # =========================================================
    # 2. [퀘스트 로직] 현재 NPC와 진행 중인 의뢰가 있는지 장부 확인
    # =========================================================
    quest_data = get_quest_status(request.npc_id)
    quest_data_to_send = None

    if quest_data:
        current_time = time.time()
        # 아직 시간이 안 지났으면 진행 중, 지났으면 방금 완료됨!
        if current_time < quest_data["completion_time"]:
            quest_data_to_send = {"status": "in_progress", "quest_name": quest_data["quest_name"]}
        else:
            quest_data_to_send = {"status": "completed_just_now", "quest_name": quest_data["quest_name"]}

    # 3. AI 뇌 호출 (기억력 + 퀘스트 메모 동시 주입!)
    ai_result = get_npc_response(
        request.npc_id, start_affinity, request.player_message,
        chat_history=recent_history, quest_data=quest_data_to_send
    )

    joined_reply = "\n".join(ai_result.get("reply", []))
    affinity_change = ai_result.get("affinity_change", 0)
    is_accepted = ai_result.get("is_request_accepted")

    # 확인용!!!! 나중엔 지우는게 정석이라고 함
    print(f"💬 [{request.npc_id}의 대답]: {joined_reply}")

    # =========================================================
    # 4. [퀘스트 로직] 방금 완료된 퀘스트라면 보상 지급 및 장부 파기
    # =========================================================
    if quest_data_to_send and quest_data_to_send["status"] == "completed_just_now":
        add_inventory_item(quest_data["quest_name"])  # 유저 가방에 아이템 쏙!
        delete_quest(request.npc_id)  # 다 끝났으니 의뢰 장부에서 삭제
        print(f"🎁 [보상 지급] '{quest_data['quest_name']}' 아이템이 인벤토리에 들어왔습니다!")

    # =========================================================
    # 5. [퀘스트 로직] 플레이어가 새로운 의뢰를 했고, NPC가 수락했다면?
    # =========================================================
    if is_accepted is True and "!의뢰" in request.player_message:
        quest_content = request.player_message.replace("!의뢰", "").strip()

        if request.npc_id == "richard":  # 촌장님은 예외 (즉시 발급)
            add_inventory_item(f"{quest_content} 허가증")
            print(f"📜 [즉시 발급] 리처드가 '{quest_content} 허가증'을 인벤토리에 넣었습니다!")
        else:
            completion_time = time.time() + 30  # 현실 시간 기준 30초 뒤 완료
            save_quest_status(request.npc_id, quest_content, "in_progress", completion_time)
            print(f"⏳ [의뢰 시작] {request.npc_id}가 '{quest_content}' 의뢰를 시작했습니다. (30초 소요)")

    # 6. 마무리 (호감도 업데이트 및 대화 기록 저장)
    final_affinity = start_affinity + affinity_change
    update_npc_affinity(request.npc_id, final_affinity)

    save_chat_message(request.npc_id, "player", request.player_message)
    save_chat_message(request.npc_id, "npc", joined_reply)

    return ChatResponse(
        npc_response=joined_reply,
        intimacy_change=affinity_change,
        final_affinity=final_affinity
    )

# 👇 [마을 기능 1] B 친구가 "여기 건물 지었어!" 하고 데이터를 보낼 때 받는 창구
@app.post("/api/build")
async def build_object(request: BuildRequest):
    # DB 창고에 물건 이름과 x, y, z 좌표를 저장합니다.
    place_object(request.object_name, request.x, request.y, request.z)
    print(f"🏠 [건설 완료] {request.object_name} 위치: ({request.x}, {request.y}, {request.z})")
    return {"message": f"{request.object_name} 건설이 서버에 저장되었습니다!"}

# 👇 [마을 기능 2] B 친구가 "게임 켰으니까 지금까지 지은 건물 다 내놔!" 할 때 주는 창구
@app.get("/api/village")
async def load_village():
    # DB 창고에서 모든 물건 리스트를 싹 다 꺼내옵니다.
    saved_objects = get_all_objects()
    print(f"🌳 [마을 불러오기] 총 {len(saved_objects)}개의 물건을 유니티로 보냅니다.")
    return {"objects": saved_objects}


@app.post("/api/system/generate-gossip")
async def trigger_gossip():
    # 1. 대화 가능한 NPC 목록 만들기
    # (참고: '치즈'는 설정상 다른 주민들과 대화가 안 되는 고양이라서 제외했습니다!)
    available_npcs = ["robin", "aina", "richard", "olivia"]

    # 2. 목록에서 겹치지 않게 랜덤으로 2명 뽑기
    npc_a, npc_b = random.sample(available_npcs, 2)

    # 3. 뽑힌 두 명으로 비밀 대화 생성하기
    gossip_content = generate_npc_gossip(npc_a, npc_b)

    # 4. DB 장부에 누구랑 누가 대화했는지 기록하기
    save_npc_gossip(npc_a, npc_b, gossip_content)

    return {
        "message": f"[{npc_a}]와(과) [{npc_b}]의 새로운 소문이 생성되었습니다!",
        "gossip": gossip_content
    }

current_time_state = "day"

@app.get("/api/time")
async def get_current_time():
    # 서버 메모장(current_time_state)에 적힌 시간을 그대로 유니티에 보내줍니다!
    return {"time_of_day": current_time_state}

# =========================================================
# ⏰ [자동화 스케줄러] 낮(20분) / 밤(10분) 사이클 무한 반복
# =========================================================
async def time_cycle_loop():
    global current_time_state
    available_npcs = ["robin", "aina", "richard", "olivia"]

    while True:
        # ☀️ 1. 낮 시간 시작 (20분 유지)
        current_time_state = "day"
        print("\n☀️ [서버 시스템] 아침이 밝았습니다! (현재: 낮 / 20분 대기)")
        await asyncio.sleep(20*60)  # 20분 대기

        # 낮 -> 밤 전환 순간! (저녁 소문 생성)
        npc_a, npc_b = random.sample(available_npcs, 2)
        print(f"🌙 [서버 시스템] 해가 집니다. {npc_a}와(과) {npc_b}가 낮에 있었던 일로 뒷담화를 시작합니다...")
        gossip_content = generate_npc_gossip(npc_a, npc_b, time_of_day="evening")
        save_npc_gossip(npc_a, npc_b, gossip_content)

        # 🌙 2. 밤 시간 시작 (10분 유지)
        current_time_state = "night"
        print("\n🌙 [서버 시스템] 밤이 깊었습니다. (현재: 밤 / 10분 대기)")
        await asyncio.sleep(10*60)  # 10분 대기

        # 밤 -> 낮 전환 순간! (아침 소문 생성)
        npc_a, npc_b = random.sample(available_npcs, 2)
        print(f"☀️ [서버 시스템] 아침이 밝아옵니다. {npc_a}와(과) {npc_b}가 간밤의 일에 대해 이야기합니다...")
        gossip_content = generate_npc_gossip(npc_a, npc_b, time_of_day="morning")
        save_npc_gossip(npc_a, npc_b, gossip_content)


# FastAPI 서버가 켜질 때, 위에서 만든 '시계(루프)'를 같이 켜주는 명령어입니다.
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(time_cycle_loop())

@app.get("/")
def read_root():
    return {"message": "마을 키우기 서버가 쌩쌩하게 돌아가는 중입니다!"}