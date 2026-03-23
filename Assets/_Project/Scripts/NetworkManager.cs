using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;

// --- 서버와 주고받을 데이터 규격 ---
[System.Serializable] 
public class ChatRequest { public string npc_id; public string player_message; }

[System.Serializable] 
public class ChatResponse { public string npc_response; public int final_affinity; }

public class NetworkManager : MonoBehaviour
{
    public static NetworkManager Instance;

    [Header("서버 설정")]
    [SerializeField] private string serverUrl = "https://lottie-unarching-marcel.ngrok-free.dev/api/chat";

    void Awake()
    {
        if (Instance == null) Instance = this; 
        else Destroy(gameObject); 
    }

    // 서버로 메시지를 보내고 대답을 처리하는 핵심 코루틴
    public IEnumerator SendChatMessage(string npcId, string message)
    {
        ChatRequest requestData = new ChatRequest
        {
            npc_id = npcId,
            player_message = message
        };

        string jsonData = JsonUtility.ToJson(requestData);
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);

        using (UnityWebRequest request = new UnityWebRequest(serverUrl, "POST"))
        {
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();

            request.SetRequestHeader("Content-Type", "application/json");
            request.SetRequestHeader("ngrok-skip-browser-warning", "true");

            // 서버 응답 대기
            yield return request.SendWebRequest();

            // 결과 처리
            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[통신 에러]: {request.error}");
                
                // [수정 부분] NPC 오브젝트를 찾아 개별 에러 메시지 가져오기
                GameObject npcObj = GameObject.Find(npcId);
                string failMessage = "서버 연결에 실패했어.";
                int currentAff = 0;

                if (npcObj != null)
                {
                    var interaction = npcObj.GetComponent<NPCInteraction>();
                    if (interaction != null) {
                        failMessage = interaction.GetFailMessage();
                        currentAff = interaction.currentAffinity;
                    }
                }
                
                // ShowServerResponse를 호출해야 '생각 중...' 애니메이션이 멈춥니다.
                DialogueManager.Instance.ShowServerResponse(failMessage, currentAff);
            }
            else
            {
                string responseText = request.downloadHandler.text;
                ChatResponse responseData = JsonUtility.FromJson<ChatResponse>(responseText);

                Debug.Log($"[서버 응답 성공] 호감도: {responseData.final_affinity}");

                // ★ [최종 수정] ShowServerResponse 하나로 통합 ★
                // 이 함수 내부에서 '생각 중' 중지 + 친밀도 업데이트 + 타이핑 효과를 모두 처리합니다.
                DialogueManager.Instance.ShowServerResponse(responseData.npc_response, responseData.final_affinity);

                /* --- [기존 코드 주석 처리] ---
                // 줄바꿈 기준으로 쪼개는 로직은 이제 DialogueManager.ShowServerResponse 내부에서 처리합니다.
                string[] parsedSentences = responseData.npc_response.Split(
                    new[] { "\n", "\r\n" },
                    System.StringSplitOptions.RemoveEmptyEntries
                );

                if (parsedSentences.Length == 0) parsedSentences = new string[] { "..." };

                // ShowDialogue를 다시 호출하면 대화창이 리셋될 수 있으므로 주석 처리합니다.
                // DialogueManager.Instance.ShowDialogue(npcId, parsedSentences, responseData.final_affinity);
                ---------------------------- */
            }
        }
    }
}