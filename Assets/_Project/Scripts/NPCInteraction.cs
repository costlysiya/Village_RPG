using UnityEngine;

public class NPCInteraction : MonoBehaviour
{
    [Header("NPC 정보 설정")]
    [Tooltip("서버 통신용 영어 ID (예: Secretary_Cat)")]
    public string npcID = "Default_Cat"; 

    [Header("친밀도 설정")]
    [Range(0, 100)]
    public int currentAffinity = 20;

    [Header("기본 대사")]
    [TextArea(3, 10)]
    public string[] introDialogues = { "안녕? 반가워!" };

    [Header("에러 메시지")]
    public string networkFailMessage = "야옹... 통신이 원활하지 않다옹.";

    private bool isPlayerNearby = false;

    void Update()
    {
        if (isPlayerNearby && Input.GetKeyDown(KeyCode.F) && !DialogueManager.Instance.dialoguePanel.activeSelf)
        {
            StartDialogue();
        }
    }

    private void StartDialogue()
    {
        // 인트로 대사 없이, "생각 중..." 상태로 바로 시작
        DialogueManager.Instance.ShowDialogueWaiting(npcID, currentAffinity);

        if (NetworkManager.Instance != null)
        {
            StartCoroutine(NetworkManager.Instance.SendChatMessage(npcID, "상호작용 시작"));
        }
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Player"))
        {
            isPlayerNearby = true;
            // 가이드 이름은 매니저를 안 거치고 여기서 바로 ID로 표시하거나 매니저 함수를 쓸 수도 있음
            DialogueManager.Instance.UpdateGuide(true, $"[F] 대화하기");
        }
    }

    private void OnTriggerExit2D(Collider2D other)
    {
        if (other.CompareTag("Player"))
        {
            isPlayerNearby = false;
            DialogueManager.Instance.UpdateGuide(false);
            DialogueManager.Instance.EndDialogueForced();
        }
    }

    public string GetFailMessage() { return networkFailMessage; }
}