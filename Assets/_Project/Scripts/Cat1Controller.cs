using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro; // TextMeshPro를 쓰기 위해 필수

public class Cat1Controller : MonoBehaviour
{
    private Animator animator;

    // 애니메이터 파라미터 인덱스 정의
    private const int IDLE = 0;
    private const int LEAKING1 = 1;
    private const int LEAKING2 = 2;
    private const int LAYING = 3;
    private const int STRETCHING = 4;
    private const int SLEEPING = 5;

    [Header("시간 설정")]
    public float normalMinTime = 3.0f;
    public float normalMaxTime = 6.0f;
    public float sleepMinTime = 15.0f;
    public float sleepMaxTime = 30.0f;
    public float stretchingTime = 1.0f; // 스트레칭 고정 시간 1초

    void Start()
    {
        animator = GetComponent<Animator>();
        if (animator != null) StartCoroutine(RandomBehaviorRoutine());
    }

    IEnumerator RandomBehaviorRoutine()
    {
        while (true)
        {
            int roll = Random.Range(0, 100);

            if (roll < 40) // 40% : IDLE
            {
                animator.SetInteger("ActionIndex", IDLE);
                yield return new WaitForSeconds(Random.Range(normalMinTime, normalMaxTime));
            }
            else if (roll < 70) // 30% : LEAKING (1 혹은 2 랜덤)
            {
                int leakIndex = Random.Range(1, 3);
                animator.SetInteger("ActionIndex", leakIndex);
                yield return new WaitForSeconds(Random.Range(normalMinTime, normalMaxTime));
            }
            else if (roll < 90) // 20% : STRETCHING (딱 1초만!)
            {
                animator.SetInteger("ActionIndex", STRETCHING);
                //Debug.Log("고양이가 시원하게 기지개를 켭니다 (1초)");
                yield return new WaitForSeconds(stretchingTime); // 1.0f 대기
            }
            else // 10% : LAYING & SLEEPING
            {
                yield return StartCoroutine(SleepSequence());
            }
        }
    }

    IEnumerator SleepSequence()
    {
        animator.SetInteger("ActionIndex", LAYING);
        yield return new WaitForSeconds(2.0f);

        animator.SetInteger("ActionIndex", SLEEPING);
        float sleepDuration = Random.Range(sleepMinTime, sleepMaxTime);
        yield return new WaitForSeconds(sleepDuration);
    }
}



