using UnityEngine;
using TMPro;

public class NPCInteraction : MonoBehaviour
{
    public string npcName = "고양이";

    [TextArea(3, 10)]
    public string[] dialogues; // 기본 대사가 필요할 경우 사용

    private bool isPlayerNearby = false;

    void Update()
    {
        // 플레이어가 근처에 있고 F키를 눌렀을 때
        if (isPlayerNearby && Input.GetKeyDown(KeyCode.F))
        {
            // 1. 서버 통신 중임을 알리는 기본 메시지 출력 (선택 사항)
            // DialogueManager.Instance.ShowDialogue(npcName, new string[] { "고양이와 연결 중..." });

            // 2. 가이드 텍스트를 [ESC] 종료 안내로 변경
            // DialogueManager의 ShowDialogue 내부에서도 호출하지만, 여기서 명시적으로 바꿔줍니다.
            DialogueManager.Instance.UpdateGuide(true, "[ESC] 대화 종료");

            // 3. 서버에 대화 시작 신호 전송
            StartCoroutine(NetworkManager.Instance.SendChatMessage(npcName, "상호작용 시작"));
        }
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Player"))
        {
            isPlayerNearby = true;

            // 플레이어가 근처에 오면 기본 가이드 UI를 띄웁니다.
            DialogueManager.Instance.UpdateGuide(true, "[F] 대화하기");
        }
    }

    private void OnTriggerExit2D(Collider2D other)
    {
        if (other.CompareTag("Player"))
        {
            isPlayerNearby = false;

            // 멀어지면 가이드 UI를 끕니다.
            DialogueManager.Instance.UpdateGuide(false);

            // 대화창이 열려있었다면 강제로 닫습니다.
            DialogueManager.Instance.EndDialogueForced();
        }
    }
}