using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class DialogueManager : MonoBehaviour
{
    public static DialogueManager Instance; // 싱글톤

    [Header("UI 연결")]
    public GameObject dialoguePanel;
    public GameObject intimacyPanel;
    public TextMeshProUGUI nameText;
    public TextMeshProUGUI contentText;
    public GameObject interactionGuide;
    public TMP_InputField inputField;

    [Header("설정")]
    public float typingSpeed = 0.05f;

    private Queue<string> sentences; // 문장들을 담아둘 FIFO 큐
    private bool isTyping = false;   // 현재 글자가 쳐지는 중인가?
    private string currentSentence;  // 현재 출력 중인 문장 전체 데이터
    private TextMeshProUGUI guideText; // 가이드 안의 실제 텍스트 컴포넌트

    [Header("하트 리스트 방식")]
    public Sprite fullHeart;   // 빨간 하트 이미지 (인스펙터에서 드래그)
    public Sprite emptyHeart;  // 회색 하트 이미지 (인스펙터에서 드래그)
    public Image[] heartImages; // 하이라키의 하트 10개를 여기에 드래그해서 넣음

    //private Dictionary<string, int> npcIntimacyData = new Dictionary<string, int>(); //npc별 호감도 저장
    // private npcIntimacy;
    private string currentTalkingNPC; // 현재 대화 중인 NPC 이름 저장용


    void Awake()
    {
        Instance = this;
        sentences = new Queue<string>();

        // 가이드 텍스트 컴포넌트 미리 찾아두기
        if (interactionGuide != null)
            guideText = interactionGuide.GetComponentInChildren<TextMeshProUGUI>();

        // 초기 상태 설정
        dialoguePanel.SetActive(false);
        intimacyPanel.SetActive(false);
        if (inputField != null) inputField.gameObject.SetActive(false);
    }

    void Update()
    {
        // 1. 대화창이 켜져 있을 때만 작동
        if (dialoguePanel.activeSelf)
        {
            // 2. ESC 키를 누르면 즉시 대화 종료 (강제 탈출)
            if (Input.GetKeyDown(KeyCode.Escape))
            {
                EndDialogueForced();
                return;
            }

            // 3. 입력창에 포커스가 없을 때만 다음 문장 넘기기
            if (inputField == null || !inputField.isFocused)
            {
                if (Input.GetKeyDown(KeyCode.Space) || Input.GetMouseButtonDown(0))
                {
                    if (isTyping)
                    {
                        StopAllCoroutines();
                        contentText.text = currentSentence;
                        isTyping = false;
                        LayoutRebuilder.ForceRebuildLayoutImmediate(dialoguePanel.GetComponent<RectTransform>());
                    }
                    else
                    {
                        DisplayNextSentence();
                    }
                }
            }
        }
    }

    // 대화 시작 (NPCInteraction에서 호출)
    public void ShowDialogue(string npcName, string[] dialogueLines, int npcIntimacy = 20)
    {
        currentTalkingNPC = npcName;

        dialoguePanel.SetActive(true);
        intimacyPanel.SetActive(true);
        nameText.text = npcName;

        // 대화 시작 시 가이드를 ESC 종료 안내로 변경
        UpdateGuide(true, "[ESC] 대화 종료");
        //해당 npc의 호감도 표시
        int heartCount = Mathf.Clamp(npcIntimacy, 0, 100) / 10;
        RefreshHeartUI(heartCount);

        sentences.Clear();
        foreach (string line in dialogueLines)
        {
            sentences.Enqueue(line);
        }

        DisplayNextSentence();
    }

    // 강제 종료 및 배경 클릭 시 호출
    public void EndDialogueForced()
    {
        StopAllCoroutines();
        sentences.Clear();
        isTyping = false;

        dialoguePanel.SetActive(false);
        intimacyPanel.SetActive(false);

        if (inputField != null)
        {
            inputField.text = "";
            inputField.DeactivateInputField();
            inputField.gameObject.SetActive(false);
        }

        // 대화가 종료되었으므로 가이드 숨기기 (멀어지면 다시 뜰 것임)
        UpdateGuide(false);
        Debug.Log("대화 강제 종료: 플레이어 조작권 복구");
    }

    public void DisplayNextSentence()
    {
        if (sentences.Count == 0)
        {
            if (inputField != null)
            {
                inputField.gameObject.SetActive(true);
                inputField.text = "";
                inputField.ActivateInputField();
            }
            return;
        }

        currentSentence = sentences.Dequeue();
        StopAllCoroutines();
        StartCoroutine(TypeSentence(currentSentence));
    }

    IEnumerator TypeSentence(string sentence)
    {
        isTyping = true;
        contentText.text = "";

        foreach (char letter in sentence.ToCharArray())
        {
            contentText.text += letter;
            yield return new WaitForSeconds(typingSpeed);
        }
        LayoutRebuilder.ForceRebuildLayoutImmediate(dialoguePanel.GetComponent<RectTransform>());
        isTyping = false;
    }

    public void OnSubmitInput()
    {
        if (inputField == null) return;

        string playerQuestion = inputField.text;
        if (string.IsNullOrWhiteSpace(playerQuestion)) return;

        // 전송 시에도 가이드는 유지되도록 함
        UpdateGuide(true, "[ESC] 대화 종료");

        StartCoroutine(NetworkManager.Instance.SendChatMessage(nameText.text, playerQuestion));

        inputField.text = "";
        inputField.DeactivateInputField();
        inputField.gameObject.SetActive(false);

        contentText.text = "고양이가 생각 중...";
    }

    // 가이드 텍스트와 활성화 여부를 한 번에 관리하는 함수
    public void UpdateGuide(bool show, string message = "")
    {
        if (interactionGuide != null)
        {
            interactionGuide.SetActive(show);
            if (show && guideText != null && !string.IsNullOrEmpty(message))
            {
                guideText.text = message;
            }
        }
    }

    // 기존 ToggleGuide는 하위 호환성을 위해 유지 (UpdateGuide 호출)
    public void ToggleGuide(bool show)
    {
        UpdateGuide(show);
    }

    public void HideDialogue()
    {
        EndDialogueForced(); // 로직 중복 방지를 위해 강제 종료 함수 호출
    }

    // 하트 UI만 새롭게 그려주는 함수
    private void RefreshHeartUI(int score)
    {
        for (int i = 0; i < heartImages.Length; i++)
        {
            heartImages[i].sprite = (i < score) ? fullHeart : emptyHeart;
        }
    }

    // 서버 응답 등에서 호감도가 변했을 때 호출
    public void UpdateIntimacy(int finalValue)
    {
        // 0~100 사이로 안전하게 제한 후 10으로 나눠 하트 개수 계산
        int heartCount = Mathf.Clamp(finalValue, 0, 100) / 10;
        RefreshHeartUI(heartCount);

        Debug.Log($"{currentTalkingNPC} 서버 최종 호감도 수신: {finalValue}점 -> 하트 {heartCount}개");
    }
}