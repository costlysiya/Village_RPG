using UnityEngine;

public class PlayerController : MonoBehaviour
{
    [Header("Movement Settings")]
    public float moveSpeed = 5f;

    private Rigidbody2D rb;
    private Vector2 moveInput;
    private Animator animator;

    void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        animator = GetComponent<Animator>();
    }

    void Start()
    {
        if (animator != null)
        {
            animator.SetFloat("LastMoveX", 0f);
            animator.SetFloat("LastMoveY", -1f);
            animator.SetFloat("Speed", 0f);
        }
    }

    void Update()
    {
        // [수정된 부분] 대화 시스템 상태 체크
        if (DialogueManager.Instance != null)
        {
            // 1. 대화창이 켜져 있는지 확인 (보통 대화창 UI 오브젝트의 활성화 여부로 판단)
            // 2. 입력창(InputField)에 포커스가 가 있는지 확인
            bool isDialogActive = DialogueManager.Instance.dialoguePanel != null && DialogueManager.Instance.dialoguePanel.activeSelf;
            bool isInputFocused = DialogueManager.Instance.inputField != null && DialogueManager.Instance.inputField.isFocused;

            if (isDialogActive || isInputFocused)
            {
                // 대화 중일 때는 입력을 0으로 초기화하고 이동 로직 건너뜀
                StopMovement();
                return;
            }
        }

        // 1. 입력 받기
        moveInput.x = Input.GetAxisRaw("Horizontal");
        moveInput.y = Input.GetAxisRaw("Vertical");

        if (moveInput.magnitude > 0.1f)
        {
            moveInput = moveInput.normalized;
        }

        // 2. 애니메이터 업데이트
        UpdateAnimation();
    }

    // 이동을 즉시 멈추고 애니메이션을 Idle로 돌리는 헬퍼 함수
    private void StopMovement()
    {
        moveInput = Vector2.zero;
        if (animator != null)
        {
            animator.SetFloat("MoveX", 0);
            animator.SetFloat("MoveY", 0);
            animator.SetFloat("Speed", 0);
        }
    }

    private void UpdateAnimation()
    {
        if (animator == null) return;

        animator.SetFloat("MoveX", moveInput.x);
        animator.SetFloat("MoveY", moveInput.y);
        animator.SetFloat("Speed", moveInput.magnitude);

        if (moveInput.magnitude > 0f)
        {
            animator.SetFloat("LastMoveX", moveInput.x);
            animator.SetFloat("LastMoveY", moveInput.y);
        }
    }

    void FixedUpdate()
    {
        rb.MovePosition(rb.position + moveInput * moveSpeed * Time.fixedDeltaTime);
    }
}