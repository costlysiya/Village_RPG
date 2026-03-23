import os
import json
import random
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
def get_npc_response(npc_id, current_affinity, user_message):
    # npc_id("robin", "cheese" 등)에 맞는 프롬프트 꺼내기
    system_instruction = npc_prompts.get(npc_id)
    
    # 등록되지 않은 npc_id가 들어오면 에러 방지
    if not system_instruction:
        return {"reply": ["(시스템: 존재하지 않는 NPC입니다.)"], "affinity_change": 0, "animation": "idle"}
    
    # 모델 세팅 (Flash Lite)
    model = genai.GenerativeModel(
        model_name='gemini-3.1-flash-lite-preview',
        system_instruction=system_instruction,
        generation_config={"temperature": 0.5}
    )

    # 운세 강제 지시 로직
    system_injection = ""
    if npc_id == "cheese" and "!운세" in user_message:
        # 파이썬이 진짜 랜덤으로 하나를 뽑음
        fortunes = ["대길", "길", "중길", "소길", "흉"]
        chosen_fortune = random.choice(fortunes)
        
        # AI에게 이번 운세가 무엇인지 강제로 지시하는 문구 생성
        system_injection = f"\n[시스템 강제 지시: 이번 턴의 운세는 반드시 '{chosen_fortune}'(으)로 설정하여 대답할 것]"
    
    # 데이터 조립 및 API 호출
    prompt = f"[현재 호감도: {current_affinity}]\n플레이어: {user_message}"
    response = model.generate_content(prompt)
    
    # JSON 파싱 / 예외 처리 방어 로직
    try:
        # 마크다운 찌꺼기(```json) 제거 후 순수 딕셔너리로 변환
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result_data = json.loads(clean_text)
        return result_data
        
    except json.JSONDecodeError:
        print(f"[파싱 에러 로그] 원본 텍스트: {response.text}")
        # 에러 시 게임이 뻗지 않도록 기본값 반환
        return {"reply": ["(시스템: NPC가 대답을 망설이고 있습니다. 다시 말 걸어주세요.)"], "affinity_change": 0, "animation": "idle"}


# =====================================================================
# 이 파일만 단독으로 실행했을 때 터미널에서 대화해 볼 수 있는 기능
# =====================================================================
if __name__ == "__main__":
    print("=== NPC 테스트 서버 ===")
    print("대화할 NPC를 선택하세요: 1.치즈(고양이) | 2.로빈(목수) | 3.아이나(식물학자) | 4.리처드(촌장) | 5.올리비아(식당 주인)")
    
    npc_map = {"1": "cheese", "2": "robin", "3": "aina", "4": "richard", "5": "olivia"}
    choice = input("번호 입력 (1~5): ").strip()
    
    target_npc = npc_map.get(choice)
    
    if target_npc:
        print(f"\n[{target_npc.upper()}] 와의 대화를 시작합니다. (종료하려면 'q' 입력)")
        # 테스트용 임시 호감도 (실제 게임에선 DB에서 가져와야 함)
        test_affinity = 20 
        
        while True:
            user_input = input("\n▶ 플레이어: ")
            if user_input.lower() == 'q':
                print("대화를 종료합니다.")
                break
                
            print(f"{target_npc}가 대답을 생각 중입니다...\n")
            
            # 
            npc_reply = get_npc_response(target_npc, test_affinity, user_input)
            
            print("=== NPC 응답 결과 ===")
            for idx, line in enumerate(npc_reply.get("reply", [])):
                print(f"대사 {idx+1}: {line}")
            print(f"호감도 변화: {npc_reply.get('affinity_change')}")
            print(f"애니메이션: {npc_reply.get('animation')}")
            
            # 테스트용 호감도 실시간 반영
            test_affinity += npc_reply.get('affinity_change', 0)
            # 호감도는 0~100 사이 유지
            test_affinity = max(0, min(100, test_affinity)) 
            print(f"(현재 누적 호감도: {test_affinity})")
            
    else:
        print("잘못된 입력입니다. 프로그램을 종료합니다.")
