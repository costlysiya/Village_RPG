using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;

// --- 서버와 주고받을 데이터 규격 ---
[System.Serializable]
public class ChatRequest
{
    public string npc_id;
    public string player_message;
}

[System.Serializable]
public class ChatResponse
{
    public string npc_response;
    //public int intimacy_change;
    public int final_affinity;
}

public class NetworkManager : MonoBehaviour
{
    public static NetworkManager Instance;

    [Header("서버 설정")]
    // ngrok에서 새로 발급받은 https 주소를 유니티 인스펙터에서 수정 가능하게 설정
    [SerializeField] private string serverUrl = "https://lottie-unarching-marcel.ngrok-free.dev/api/chat";

    void Awake()
    {
        if (Instance == null) Instance = this;
        else Destroy(gameObject);
    }

    void Start()
    {
        Debug.Log("서버 통신 시스템 준비 완료!");
        // 테스트가 필요 없다면 아래 줄은 주석 처리해도 됩니다.
        //StartCoroutine(SendChatMessage("blacksmith", "안녕? 마을에 처음 왔어."));
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

            // [바뀐 부분 1] 필수 헤더 설정
            request.SetRequestHeader("Content-Type", "application/json");

            // [바뀐 부분 2] ngrok의 브라우저 경고창을 우회하는 핵심 헤더!
            request.SetRequestHeader("ngrok-skip-browser-warning", "true");

            // 서버 응답 대기
            yield return request.SendWebRequest();

            // 결과 처리
            if (request.result == UnityWebRequest.Result.ConnectionError || request.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"[통신 에러]: {request.error}");
                DialogueManager.Instance.ShowDialogue(npcId, new string[] { "서버 연결에 실패했어. 주소나 네트워크를 확인해줘!" });
            }
            else
            {
                // [바뀐 부분 3] 성공 시 데이터를 파싱해서 DialogueManager로 전달
                string responseText = request.downloadHandler.text;
                ChatResponse responseData = JsonUtility.FromJson<ChatResponse>(responseText);

                Debug.Log($"[서버 응답 성공] 호감도: {responseData.final_affinity}");
                DialogueManager.Instance.UpdateIntimacy(responseData.final_affinity);


                // 줄바꿈(\n) 기준으로 문장 쪼개기 (엔터 칠 때마다 다음 대사로 넘어가게 함)
                string[] parsedSentences = responseData.npc_response.Split(
                    new[] { "\n", "\r\n" },
                    System.StringSplitOptions.RemoveEmptyEntries
                );

                // 만약 대답이 비어있으면 기본값 출력
                if (parsedSentences.Length == 0)
                {
                    parsedSentences = new string[] { "..." };
                }

                // UI에 고양이의 대답을 한 문장씩 띄워줌
                DialogueManager.Instance.ShowDialogue(npcId, parsedSentences, responseData.final_affinity);
            }
        }
    }
}