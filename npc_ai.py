import os
import json
import random
import time  # A 친구가 추가한 모듈
import google.generativeai as genai
from dotenv import load_dotenv
from prompts import npc_prompts
from database import get_random_unheard_gossip, mark_gossip_as_heard

# API 키 세팅
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)


# =====================================================================
# 서버 담당자 용
# 유니티에서 통신이 오면 서버(FastAPI 등)가 이 함수를 호출해서 결과를 받아감
# =====================================================================
# 👇 [융합 포인트 1] 다은님의 'chat_history'와 친구의 'quest_data'를 모두 받도록 합쳤습니다!
def get_npc_response(npc_id, current_affinity, user_message, chat_history=None, quest_data=None):
    # npc_id("robin", "Yellow Cat" 등)에 맞는 프롬프트 꺼내기
    system_instruction = npc_prompts.get(npc_id)

    # 등록되지 않은 npc_id가 들어오면 에러 방지
    if not system_instruction:
        return {"reply": ["(시스템: 존재하지 않는 NPC입니다.)"], "affinity_change": 0, "animation": "idle",
                "is_request_accepted": None}

    # ---------------------------------------------------------
    # [소문 로직] DB에서 아직 안 들은 소문 몰래 가져오기
    # ---------------------------------------------------------
    gossip_data = get_random_unheard_gossip()
    gossip_text = ""
    gossip_id = None

    if gossip_data:
        gossip_id, from_npc, content = gossip_data
        # AI 프롬프트에 몰래 지시사항을 끼워 넣습니다.
        gossip_text = f"\n[특별 시스템 지시사항: 당신은 최근 마을에서 '{content}' 라는 소문을 들었습니다. 플레이어의 말에 대답하면서 이 소문 내용을 아주 자연스럽게 슬쩍 언급해 주세요! 단, 출력 형식(JSON)은 절대 망가뜨리지 마세요.]\n"

    # 모델 세팅 (Flash Lite)
    model = genai.GenerativeModel(
        model_name='gemini-3.1-flash-lite-preview',
        system_instruction=system_instruction,
        generation_config={"temperature": 0.5}
    )

    # ---------------------------------------------------------
    # [핵심 로직] 시스템 메모(쪽지) 및 대화 기억 조립
    # ---------------------------------------------------------
    system_memo = ""

    # 👇 [추가된 부분 1] 기껏 가져온 소문 지시사항을 메모장에 붙여줍니다!
    if gossip_text:
        system_memo += gossip_text

    # 1. 운세 강제 지시 로직
    if npc_id == "Yellow Cat" and "!운세" in user_message:
        fortunes = ["대길", "길", "중길", "소길", "흉"]
        chosen_fortune = random.choice(fortunes)
        system_memo += f"\n[시스템 강제 지시: 이번 턴의 운세는 반드시 '{chosen_fortune}'(으)로 설정하여 대답할 것]"

    # 2. 퀘스트(의뢰) 상태 지시 로직
    if quest_data:
        if quest_data["status"] == "in_progress":
            system_memo += f"\n[시스템 강제 지시: 너는 현재 플레이어의 의뢰('{quest_data['quest_name']}')를 수행 중이다. 아직 완성되지 않았으니 작업 중이라고 대답해라.]"
        elif quest_data["status"] == "completed_just_now":
            system_memo += f"\n[시스템 강제 지시: 방금 '{quest_data['quest_name']}' 의뢰가 완료되었다! 결과물을 건네주며 생색을 내거나 뿌듯해하는 대사를 해라.]"

    # 3. 과거 대화 기록 추가 로직
    history_text = ""
    if chat_history:
        history_text = "\n[최근 대화 기록]\n"
        for speaker, msg in chat_history:
            role = "플레이어" if speaker == "player" else "너(NPC)"
            history_text += f"{role}: {msg}\n"
    else:
        history_text = "\n[최근 대화 기록]\n없음 (이번이 첫 대화야!)\n"

    # 데이터 조립 및 API 호출 (기억력 + 퀘스트 메모 + 소문 융합)
    prompt = f"[현재 호감도: {current_affinity}]{history_text}{system_memo}\n플레이어: {user_message}"
    response = model.generate_content(prompt)

    # JSON 파싱 / 예외 처리 방어 로직
    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result_data = json.loads(clean_text)

        # 👇 [추가된 부분 2] AI가 대답을 성공적으로 만들었으니, DB 장부에 '읽었음' 체크!
        if gossip_id is not None:
            mark_gossip_as_heard(gossip_id)

        return result_data

    except json.JSONDecodeError:
        print(f"[파싱 에러 로그] 원본 텍스트: {response.text}")
        return {"reply": ["(시스템: NPC가 대답을 망설이고 있습니다. 다시 말 걸어주세요.)"], "affinity_change": 0, "animation": "idle",
                "is_request_accepted": None}



# npc_ai.py의 소문 생성기 수정

# 파라미터에 time_of_day="evening" (낮->밤) 을 추가했습니다.
def generate_npc_gossip(npc_a_id, npc_b_id, time_of_day="evening"):
    prompt_a = npc_prompts.get(npc_a_id, "설정 없음")
    prompt_b = npc_prompts.get(npc_b_id, "설정 없음")

    model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

    # 👇 [핵심] 시간대에 맞춰 AI에게 주는 상황(Context)을 바꿉니다!
    if time_of_day == "evening":
        time_context = "[상황] 하루 해가 저물고 밤이 되었습니다. 두 사람이 일과를 마치고 쉬면서, '오늘 낮에 있었던 일'이나 '낮에 플레이어가 한 행동'에 대해 뒷담화를 나눕니다."
    else:  # "morning" (밤->낮)
        time_context = "[상황] 아침이 밝았습니다. 두 사람이 아침 일찍 만나, '어젯밤에 들렸던 이상한 소리', '간밤의 꿈', 또는 '오늘 하루의 계획'에 대해 은밀히 이야기합니다."

    prompt = f"""
    당신은 게임 속 두 NPC의 대화를 작성하는 드라마 작가입니다.
    아래는 두 NPC의 완벽한 성격과 말투, 세계관 설정입니다.

    [NPC A 설정]
    {prompt_a}

    [NPC B 설정]
    {prompt_b}

    {time_context}

    [작성 규칙]
    - 위 설정된 성격과 말투를 완벽하게 반영하여 티키타카가 되는 짧은 대화문(3~4줄)을 작성하세요.
    - JSON 양식을 무시하고, 아래 [형식]에 맞춰 일반 텍스트로만 출력하세요.

    [형식]
    대화:
    (대사 내용)

    요약: (이 대화를 다른 사람이 들었을 때 낼 만한 '한 줄짜리 소문' 작성)
    """

    response = model.generate_content(prompt)
    text = response.text
    print(f"\n🎭 [비밀 대화 발생] {npc_a_id}와(과) {npc_b_id}가 만났습니다:\n{text}\n")

    if "요약:" in text:
        summary = text.split("요약:")[1].strip()
        return summary
    return "별다른 소문이 없습니다."

# =====================================================================
# 이 파일만 단독으로 실행했을 때 터미널에서 대화해 볼 수 있는 기능
# =====================================================================
if __name__ == "__main__":
    print("=== NPC 테스트 서버 ===")
    print("대화할 NPC를 선택하세요: 1.치즈(고양이) | 2.로빈(목수) | 3.아이나(식물학자) | 4.리처드(촌장) | 5.올리비아(식당 주인)")

    # 👇 [융합 포인트 2] 치즈의 아이디를 DB에 맞게 "Yellow Cat"으로 수정했습니다.
    npc_map = {"1": "Yellow Cat", "2": "robin", "3": "aina", "4": "richard", "5": "olivia"}
    choice = input("번호 입력 (1~5): ").strip()

    target_npc = npc_map.get(choice)

    if target_npc:
        print(f"\n[{target_npc.upper()}] 와의 대화를 시작합니다. (종료하려면 'q' 입력)")
        test_affinity = 20

        # 테스트용 가상 DB 생성 (A 친구 코드 그대로 사용)
        mock_db = {
            "is_working": False,
            "quest_name": "",
            "completion_time": 0
        }

        while True:
            user_input = input("\n▶ 플레이어: ")
            if user_input.lower() == 'q':
                print("대화를 종료합니다.")
                break

            print(f"{target_npc}가 대답을 생각 중입니다...\n")

            current_time = time.time()
            quest_data_to_send = None

            if mock_db["is_working"]:
                if current_time < mock_db["completion_time"]:
                    quest_data_to_send = {"status": "in_progress", "quest_name": mock_db["quest_name"]}
                else:
                    quest_data_to_send = {"status": "completed_just_now", "quest_name": mock_db["quest_name"]}

            # 👇 [융합 포인트 3] 테스트 터미널에서는 과거 기록(chat_history)을 일단 빈 리스트([])로 넘겨줍니다.
            npc_reply = get_npc_response(target_npc, test_affinity, user_input, chat_history=[],
                                         quest_data=quest_data_to_send)

            if quest_data_to_send and quest_data_to_send["status"] == "completed_just_now":
                print(f"[서버 시스템: 유저 인벤토리에 '{mock_db['quest_name']}' 아이템이 지급되었습니다!]")
                print(f"[서버 시스템: 유저 인벤토리에 '{mock_db['quest_name']}' 아이템이 지급되었습니다!]")
                mock_db["is_working"] = False

            print("=== NPC 응답 결과 ===")
            for idx, line in enumerate(npc_reply.get("reply", [])):
                print(f"대사 {idx + 1}: {line}")
            print(f"호감도 변화: {npc_reply.get('affinity_change')}")
            print(f"애니메이션: {npc_reply.get('animation')}")
            print(f"의뢰 수락 여부: {npc_reply.get('is_request_accepted')}")

            is_accepted = npc_reply.get("is_request_accepted")
            if is_accepted is True and "!의뢰" in user_input:
                quest_content = user_input.replace("!의뢰", "").strip()

                if target_npc == "richard":
                    print(f"\n[서버 시스템: '{target_npc}'가 허가했습니다! 즉시 인벤토리에 '{quest_content} 허가증'이 지급됩니다!]")
                else:
                    print(f"\n[서버 시스템: '{target_npc}'가 의뢰를 수락했습니다! 30초 타이머를 시작합니다.]")
                    mock_db["is_working"] = True
                    mock_db["quest_name"] = quest_content
                    mock_db["completion_time"] = time.time() + 30

            elif is_accepted is False and "!의뢰" in user_input:
                print("\n[서버 시스템: NPC가 의뢰를 거절했습니다. DB에 저장하지 않습니다.]")

            test_affinity += npc_reply.get('affinity_change', 0)
            test_affinity = max(0, min(100, test_affinity))
            print(f"(현재 누적 호감도: {test_affinity})")

    else:
        print("잘못된 입력입니다. 프로그램을 종료합니다.")