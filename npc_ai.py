import os
import json
import random
import time  # A 친구가 추가한 모듈
import google.generativeai as genai
from dotenv import load_dotenv

from prompts import npc_prompts

# API 키 세팅
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)


# =====================================================================
# 서버 담당자 용
# 유니티에서 통신이 오면 서버(FastAPI 등)가 이 함수를 호출해서 결과를 받아감
# =====================================================================
# 'chat_history', 'quest_data', 그리고 'daily_rumor'까지 모두 받도록 수정
def get_npc_response(npc_id, current_affinity, user_message, chat_history=None, quest_data=None, daily_rumor=None):
    # npc_id("robin", "Yellow Cat" 등)에 맞는 프롬프트 꺼내기
    system_instruction = npc_prompts.get(npc_id)

    # 등록되지 않은 npc_id가 들어오면 에러 방지
    if not system_instruction:
        return {"reply": ["(시스템: 존재하지 않는 NPC입니다.)"], "affinity_change": 0, "animation": "idle",
                "is_request_accepted": None}

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

    # 1. 운세 강제 지시 로직 (Yellow Cat으로 통일)
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

    # 3. [추가] 오늘의 마을 소문 주입 로직
    if daily_rumor:
        system_memo += f"\n[시스템 강제 지시: 현재 마을에 '{daily_rumor}'라는 소문이 돌고 있다. 대화 중 자연스럽게 이 소문을 언급하거나 너의 의견을 덧붙여라.]"

    # 4. 과거 대화 기록 추가 로직
    history_text = ""
    if chat_history:
        history_text = "\n[최근 대화 기록]\n"
        for speaker, msg in chat_history:
            role = "플레이어" if speaker == "player" else "너(NPC)"
            history_text += f"{role}: {msg}\n"
    else:
        history_text = "\n[최근 대화 기록]\n없음 (이번이 첫 대화야!)\n"

    # 데이터 조립 및 API 호출
    prompt = f"[현재 호감도: {current_affinity}]{history_text}{system_memo}\n플레이어: {user_message}"
    response = model.generate_content(prompt)

    # JSON 파싱 / 예외 처리 방어 로직
    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result_data = json.loads(clean_text)
        return result_data

    except json.JSONDecodeError:
        print(f"[파싱 에러 로그] 원본 텍스트: {response.text}")
        return {"reply": ["(시스템: NPC가 대답을 망설이고 있습니다. 다시 말 걸어주세요.)"], "affinity_change": 0, "animation": "idle",
                "is_request_accepted": None}


# =====================================================================
# [추가] 밤 시간대 NPC 소문 생성 시뮬레이션 (Multi-Agent System)
# =====================================================================
def generate_daily_rumor(npc1_id, npc2_id, topic):
    print(f"\n[서버 백그라운드: 마을의 밤이 찾아왔습니다. {npc1_id}와(과) {npc2_id}의 뒷담화 시뮬레이션을 시작합니다...]")
    chat_log = ""
    
    # 첫 대화 트리거
    current_message = f"[시스템 강제 지시: 상대방에게 '{topic}'에 대해 먼저 말을 걸어봐. 반드시 질문이나 불평으로 끝내라.]"

    # 2턴 동안 서로 대화 (핑퐁)
    for i in range(2):
        # NPC 1의 턴
        resp1 = get_npc_response(npc1_id, current_affinity=50, user_message=current_message)
        reply1 = " ".join(resp1.get("reply", []))
        chat_log += f"{npc1_id}: {reply1}\n"
        print(f"[{npc1_id}]: {reply1}")

        # NPC 2에게 전달할 메시지 세팅
        current_message = f"[상대방의 말: '{reply1}']\n이 말에 이어서 대답해."
        
        # NPC 2의 턴
        resp2 = get_npc_response(npc2_id, current_affinity=50, user_message=current_message)
        reply2 = " ".join(resp2.get("reply", []))
        chat_log += f"{npc2_id}: {reply2}\n"
        print(f"[{npc2_id}]: {reply2}")
        
        # 다음 턴을 위해 메시지 교체
        current_message = f"[상대방의 말: '{reply2}']\n이 말에 이어서 대답해."

    print("\n[서버 백그라운드: 대화를 바탕으로 오늘의 소문을 요약합니다...]")
    
    # 요약 전용 모델 호출 (Flash 모델 권장)
    summarizer_model = genai.GenerativeModel('gemini-1.5-flash')
    summary_prompt = f"다음 마을 주민들의 대화 내용을 바탕으로, 다른 마을 사람들이 수군거릴 법한 '한 줄짜리 소문(가십)'을 만들어줘:\n{chat_log}"
    
    summary_response = summarizer_model.generate_content(summary_prompt)
    rumor = summary_response.text.strip()
    
    print(f"⭐ [오늘의 소문]: {rumor}\n")
    return rumor


# =====================================================================
# 이 파일만 단독으로 실행했을 때 터미널에서 대화해 볼 수 있는 기능
# =====================================================================
if __name__ == "__main__":
    print("=== NPC 테스트 서버 ===")
    print("대화할 NPC를 선택하세요: 1.치즈(고양이) | 2.로빈(목수) | 3.아이나(식물학자) | 4.리처드(촌장) | 5.올리비아(식당 주인)")

    npc_map = {"1": "Yellow Cat", "2": "robin", "3": "aina", "4": "richard", "5": "olivia"}
    choice = input("번호 입력 (1~5): ").strip()

    target_npc = npc_map.get(choice)

    if target_npc:
        print(f"\n[{target_npc.upper()}] 와의 대화를 시작합니다. (종료하려면 'q' 입력)")
        print("팁: 대화 중 '!밤' 이라고 입력하면 무작위 두 주민이 대화를 나누고 소문을 만듭니다.")
        
        test_affinity = 20
        current_daily_rumor = None  # 초기 소문은 없음

        # 테스트용 가상 DB 생성
        mock_db = {
            "is_working": False,
            "quest_name": "",
            "completion_time": 0
        }
        
        # 대화 내용을 저장할 세션 메모리 변수 추가
        session_chat_history = []

        while True:
            user_input = input("\n▶ 플레이어: ")
            
            if user_input.lower() == 'q':
                print("대화를 종료합니다.")
                break
            
            # 랜덤 NPC 대화 트리거 
            if user_input == '!밤':
                # 고양이(Yellow Cat)를 제외한 인간 NPC 목록
                human_villagers = ["robin", "aina", "richard", "olivia"]
                
                # 랜덤으로 2명 뽑기
                npc1, npc2 = random.sample(human_villagers, 2)
                
                # 대화 주제도 랜덤으로 설정
                topics = [
                    "최근 마을의 날씨", 
                    "어제 식당 근처에 흘려진 이상한 물건", 
                    "요즘 촌장님의 잔소리", 
                    "가장 좋아하는 음식",
                    "마을 한가운데 있는 고목나무의 상태"
                ]
                random_topic = random.choice(topics)
                
                # 시뮬레이션 돌려서 소문 생성
                current_daily_rumor = generate_daily_rumor(npc1, npc2, random_topic)
                print("💡 NPC들에게 말을 걸어 소문에 대해 물어보세요! (예: 마을에 무슨 재밌는 일 없어?)")
                continue

            print(f"{target_npc}가 대답을 생각 중입니다...\n")

            current_time = time.time()
            quest_data_to_send = None

            if mock_db["is_working"]:
                if current_time < mock_db["completion_time"]:
                    quest_data_to_send = {"status": "in_progress", "quest_name": mock_db["quest_name"]}
                else:
                    quest_data_to_send = {"status": "completed_just_now", "quest_name": mock_db["quest_name"]}

            # daily_rumor를 포함해서 API 호출
            npc_reply = get_npc_response(
                npc_id=target_npc, 
                current_affinity=test_affinity, 
                user_message=user_input, 
                chat_history=session_chat_history,
                quest_data=quest_data_to_send,
                daily_rumor=current_daily_rumor
            )

            if quest_data_to_send and quest_data_to_send["status"] == "completed_just_now":
                print(f"[서버 시스템: 유저 인벤토리에 '{mock_db['quest_name']}' 아이템이 지급되었습니다!]")
                mock_db["is_working"] = False

            print("=== NPC 응답 결과 ===")
            
            # NPC 대사를 합쳐서 하나의 문자열로 만들기 (기록용)
            npc_full_reply = ""
            
            for idx, line in enumerate(npc_reply.get("reply", [])):
                print(f"대사 {idx + 1}: {line}")
                npc_full_reply += line + " "
                
            print(f"호감도 변화: {npc_reply.get('affinity_change')}")
            print(f"애니메이션: {npc_reply.get('animation')}")
            print(f"의뢰 수락 여부: {npc_reply.get('is_request_accepted')}")

            # 이번 턴의 대화를 기록에 추가
            session_chat_history.append(("player", user_input))
            session_chat_history.append(("npc", npc_full_reply.strip()))
            
            # 토큰이 너무 길어지는 것을 방지하기 위해 최근 5번의 턴(플레이어5+NPC5 = 10개)만 유지
            if len(session_chat_history) > 10:
                session_chat_history = session_chat_history[-10:]

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
