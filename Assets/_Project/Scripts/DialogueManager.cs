using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class DialogueManager : MonoBehaviour
{
    public static DialogueManager Instance;

    [Header("UI 연결")]
    public GameObject dialoguePanel;
    public GameObject intimacyPanel;
    public TextMeshProUGUI nameText;
    public TextMeshProUGUI contentText;
    public GameObject interactionGuide;
    public TMP_InputField inputField;

    [Header("설정")]
    public float typingSpeed = 0.05f;

    [Header("하트 리스트")]
    public Sprite fullHeart;
    public Sprite emptyHeart;
    public Image[] heartImages;

    private Queue<string> sentences;
    private bool isTyping = false;
    private bool isWaitingForServer = false;
    private string currentSentence;
    private string currentTalkingNPCId; // 서버 전송용 ID 저장

    void Awake()
    {
        Instance = this;
        sentences = new Queue<string>();
        dialoguePanel.SetActive(false);
        intimacyPanel.SetActive(false);
        
        if (inputField != null)
        {
            inputField.gameObject.SetActive(false);
            inputField.onSubmit.AddListener(delegate { OnSubmitInput(); });
        }
    }

    // ID를 한글 이름으로 바꿔주는 헬퍼 함수
    private string GetKoreanName(string id)
    {
        switch (id)
        {
            case "Yellow Cat": return "치즈";
            case "robin":      return "로빈";
            case "aina": return "아이나";
            case "richard": return "리처드";
            default:              return "NPC";
        }
    }

void Update()
{
    if (dialoguePanel.activeSelf && !isWaitingForServer)
    {
        if (Input.GetKeyDown(KeyCode.Escape)) { EndDialogueForced(); return; }

        // ★ 예전 코드처럼 isFocused로 체크
        if (inputField == null || !inputField.isFocused)
        {
            if (Input.GetKeyDown(KeyCode.Space) || Input.GetMouseButtonDown(0))
            {
                if (isTyping)
                {
                    StopAllCoroutines();
                    contentText.text = currentSentence;
                    isTyping = false;
                    LayoutRebuilder.ForceRebuildLayoutImmediate(
                        dialoguePanel.GetComponent<RectTransform>());
                }
                else
                {
                    DisplayNextSentence();
                }
            }
        }
    }
}

    private bool justStarted = false;
    public void ShowDialogue(string npcId, string[] dialogueLines, int npcIntimacy)
    {
        currentTalkingNPCId = npcId;
        dialoguePanel.SetActive(true);
        intimacyPanel.SetActive(true);
        
        nameText.text = GetKoreanName(npcId); // UI에는 한글 이름
        UpdateGuide(true, "[ESC] 대화 종료");
        RefreshHeartUI(npcIntimacy / 10);

        if (inputField != null) inputField.gameObject.SetActive(false);

        sentences.Clear();
        foreach (string line in dialogueLines) sentences.Enqueue(line);
        justStarted = true;
        DisplayNextSentence();
    }

    public void DisplayNextSentence()
    {
        // isTyping 가드는 유지해도 OK
        if (isTyping) return;

        if (sentences.Count == 0)
        {
            // ★ activeSelf 체크 제거 — 예전처럼 단순하게
            if (inputField != null)
            {
                inputField.gameObject.SetActive(true);
                inputField.text = "";
                inputField.ActivateInputField();
            }
            return;
        }

        if (inputField != null) inputField.gameObject.SetActive(false);

        currentSentence = sentences.Dequeue();
        StopAllCoroutines();
        StartCoroutine(TypeSentence(currentSentence));
    }

    public void OnSubmitInput()
    {
        if (inputField == null || string.IsNullOrWhiteSpace(inputField.text)) return;
        if (isWaitingForServer) return;

        string question = inputField.text;
        // 저장된 영어 ID로 서버 통신
        StartCoroutine(NetworkManager.Instance.SendChatMessage(currentTalkingNPCId, question));

        inputField.text = "";
        inputField.gameObject.SetActive(false); 
        isWaitingForServer = true;
        StartCoroutine(WaitingDotsAnimation());
    }

    public void ShowServerResponse(string response, int affinity)
    {
        isWaitingForServer = false;
        StopAllCoroutines();
        UpdateIntimacy(affinity);

        string[] parsedSentences = response.Split(new[] { "\n", "\r\n" }, System.StringSplitOptions.RemoveEmptyEntries);
        sentences.Clear();
        foreach (string line in parsedSentences) sentences.Enqueue(line);
        
        DisplayNextSentence();
    }

    IEnumerator TypeSentence(string s)
    {
        isTyping = true;
        contentText.text = "";
        foreach (char c in s.ToCharArray())
        {
            contentText.text += c;
            yield return new WaitForSeconds(typingSpeed);
        }
        isTyping = false;
    }

    IEnumerator WaitingDotsAnimation()
    {
        string baseText = $"{GetKoreanName(currentTalkingNPCId)}(이)가 생각 중";
        while (isWaitingForServer)
        {
            contentText.text = baseText + "."; yield return new WaitForSeconds(0.5f);
            if (!isWaitingForServer) break;
            contentText.text = baseText + ".."; yield return new WaitForSeconds(0.5f);
            if (!isWaitingForServer) break;
            contentText.text = baseText + "..."; yield return new WaitForSeconds(0.5f);
        }
    }

    public void ShowDialogueWaiting(string npcId, int npcIntimacy)
    {   
        currentTalkingNPCId = npcId;
        dialoguePanel.SetActive(true);
        intimacyPanel.SetActive(true);
        nameText.text = GetKoreanName(npcId);
        UpdateGuide(true, "[ESC] 대화 종료");
        RefreshHeartUI(npcIntimacy / 10);

        if (inputField != null) inputField.gameObject.SetActive(false);

        sentences.Clear();
        isWaitingForServer = true;
        StartCoroutine(WaitingDotsAnimation());
    }

    public void EndDialogueForced() { isWaitingForServer = false; StopAllCoroutines(); dialoguePanel.SetActive(false); intimacyPanel.SetActive(false); UpdateGuide(false); }
    private void RefreshHeartUI(int s) { for (int i = 0; i < heartImages.Length; i++) heartImages[i].sprite = (i < s) ? fullHeart : emptyHeart; }
    public void UpdateIntimacy(int v) { RefreshHeartUI(Mathf.Clamp(v, 0, 100) / 10); }
    public void UpdateGuide(bool s, string m = "") { if (interactionGuide != null) { interactionGuide.SetActive(s); var t = interactionGuide.GetComponentInChildren<TextMeshProUGUI>(); if(s && t != null) t.text = m; } }
}