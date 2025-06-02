# 🔎NS3 Coder: LLM 기반의 네트워크 시뮬레이션 코드 자동 생성  

## 배경 및 목적  
 최근 End-user 디바이스 성능 향상과 함께 다양한 Application들이 등장하며, 이를 지원하기 위한 네트워크 설계와 운영 환경도 점점 더 복잡해지고 있다. 
이러한 문제를 해결하기 위한 대안으로 LLM(Large Language Model) 기반 접근이 주목받고 있으며, LLM의 자연어 이해와 추론 능력을 바탕으로 네트워크 도메인에도 효과적으로 적용될 수 있다. 
이에 본 프로젝트를 통해 LLM을 활용하여 NS-3 네트워크 시뮬레이션 코드를 자동 생성하는 프레임워크 ‘NS3 Coder’를 설계하였으며, 전문 도메인에 특화된 실험 자동화 가능성을 제시하고자 한다.  

## Framework 
<img width="1032" alt="image" src="https://github.com/user-attachments/assets/32f3dbbd-ffe0-4c41-b091-f9b7ef6c3371" />

## 내용 
 NS3 Coder 프레임워크는 입력 분석(Analyzer), 코드 생성(Code Generator), 코드 검증(Verifier)의 세 단계로 구성된다.    
 
**1. 입력 분석(Analyzer)** : 사용자의 자연어 입력을 분석하여 실험 목적, 네트워크 구성, 파라미터 등을 구조화된 형태로 추출한다.  

**2. 코드 생성(Code Generator)** : 분석된 정보를 바탕으로 LLM을 활용해 NS-3에서 실행 가능한 시뮬레이션 코드를 생성한다.  

**3. 코드 검증(Verifier)** : 생성된 코드가 논리적·구문적으로 타당한지 확인하고, 실행 가능 여부를 검토한다. 만일 오류가 발견되면 해당 부분의 문제와 해결 방안을 모색하여 Code Generator로 feedback 절차를 수행한다.

</br></br>
# 📆진행 계획 (~5/8)
![image (1)](https://github.com/user-attachments/assets/9589cf20-f8ce-4553-921c-1fe656c512ea)

  
# 📑진행 상황

| Date           | Name                                             | Files & media                  |
|----------------|--------------------------------------------------|--------------------------------|
| March 19, 2025 | 방학 동안 했던 내용                              | [20250319_수화.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250319_%EC%88%98%ED%99%94.pdf), [20250319_희원.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250319_%ED%9D%AC%EC%9B%90.pdf)      |
| March 26, 2025 | 입력 양식 정의 및 Default 조사, RAG 적용 및 결과 | [20250326.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250326.pdf)         |
| April 30, 2025 | fine-tuning, RAG DB 구성, Data Cleaning, ns-3   | [20250430(1).pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250430%20(1).pdf), [20250430(2).pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250430%20(2).pdf) |
| May 7, 2025    | Data Cleaning, RAG 적용 결과                     | [20250507.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250507.pdf)              |
| May 14, 2025   | RAG DB 관련                                     | [20250514.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250514.pdf)            |
| May 21, 2025   | LLaVa finetuning(GBC), DB crawling(ns3 community)| [20250521.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250521.pdf)             |
| May 28, 2025   | Data crawling(stackoverflow)                    | [20250528.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/20250528.pdf) |  
| June 2, 2025   | 2025-1 창의작품경진대회 발표자료(NS3 Coder)       | [NS3-Coder_2025학년도-1학기_창의작품경진대회_Gardening_.pdf](https://github.com/o4e3/NS3-Coder/blob/main/docs/NS3-Coder_2025%EB%85%84%EB%8F%84-1%ED%95%99%EA%B8%B0_%EC%B0%BD%EC%9D%98%EC%9E%91%ED%92%88%EA%B2%BD%EC%A7%84%EB%8C%80%ED%9A%8C_Gardening_.pdf) |


 
