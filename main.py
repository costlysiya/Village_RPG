from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from npc_ai import get_npc_response     #ai함수 가져옴
from database import get_npc_affinity, update_npc_affinity  #db 불러옴

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


# 4. 채팅 API 엔드포인트
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_npc(request: ChatRequest):
    print(f"\n[{request.npc_id}에게 온 메시지]: {request.player_message}")

    # 1. 시작 호감도
    start_affinity = get_npc_affinity(request.npc_id)

    # 2. AI에게 질문 던지기
    ai_result = get_npc_response(request.npc_id, start_affinity, request.player_message)

    joined_reply = "\n".join(ai_result.get("reply", []))
    affinity_change = ai_result.get("affinity_change", 0)

    # 3. 이번 대화로 계산된 최종 호감도
    final_affinity = start_affinity + affinity_change

    # 계산이 끝난 최종 호감도를 다시 db에 update
    update_npc_affinity(request.npc_id, final_affinity)

    print(f"[AI 응답 완료]: {joined_reply}")

    # 👇 [여기에 추가!] 파이참 디버그창에 호감도 상태를 예쁘게 출력합니다.
    print(f"👉 [디버그] {request.npc_id} 호감도: {start_affinity} -> {final_affinity} (변화량: {affinity_change})")

    # 유니티로 최종 결과 전송
    return ChatResponse(
        npc_response=joined_reply,
        intimacy_change=affinity_change,
        final_affinity=final_affinity
    )

@app.get("/")
def read_root():
    return {"message": "마을 키우기 서버가 쌩쌩하게 돌아가는 중입니다!"}