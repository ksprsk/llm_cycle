# AI Debate System (llm_cycle)

이 프로젝트는 여러 AI 모델 간의 구조화된 협업 시스템을 구현합니다. 각 AI 모델은 주어진 주제에 대해 3단계(제안, 비판 및 선별, 종합) 접근 방식을 따라 솔루션을 개선합니다. 시스템은 웹 인터페이스(Streamlit)와 명령줄 인터페이스를 모두 제공합니다.

## 핵심 기능

* **구조화된 3단계 토론:**
    1.  **제안 (Propose):** 첫 번째 AI가 주제와 관련된 다양한 아이디어를 생성합니다 (양적 집중).
    2.  **비판 및 선별 (Critique & Filter):** 두 번째 AI가 제안된 아이디어를 검토하고, 개선하며, 가치 있는 것을 선별합니다 (질적 집중).
    3.  **종합 (Synthesize):** 세 번째 AI가 선별된 아이디어를 체계적이고 실행 가능한 최종 솔루션으로 구성합니다 (구성 집중).
* **다중 모델 지원:** `config.json`을 통해 여러 AI 모델(OpenAI, Claude, Gemini 등 호환 API 사용 모델)을 쉽게 구성할 수 있습니다.
* **웹 인터페이스:** Streamlit을 사용하여 토론을 시작하고, 기록을 보고, 검색하고, 관리할 수 있는 사용자 친화적인 UI를 제공합니다.
* **명령줄 인터페이스:** 대화형 토론 세션을 실행하거나 과거 토론 기록을 키워드 및 날짜 범위로 검색할 수 있습니다.
* **기록 관리:** 토론 세션을 자동으로 저장하고, 불러오고, 검색하고, 스냅샷을 생성하고, 삭제할 수 있습니다. (`debate_history/` 디렉토리)
* **구성 가능성:** 모델별 API 키, 엔드포인트 URL, 최대 토큰 등을 `config.json`에서 설정할 수 있습니다.

## 설정

1.  **리포지토리 복제:**
    ```bash
    git clone <your-repository-url> llm_cycle
    cd llm_cycle
    ```

2.  **종속성 설치:**
    ```bash
    pip install -r requirements.txt
    ```
    *(필요한 라이브러리: `openai`, `python-dotenv`, `streamlit`)*

3.  **모델 구성:**
    * `config.example.json` 파일을 복사하여 `config.json` 파일을 생성합니다.
    * `config.json` 파일을 열고 사용할 각 AI 모델의 설정을 추가하거나 수정합니다. **API 키는 `api_key` 필드에 직접 입력해야 합니다.**
        ```json
        {
          "models": [
            {
              "name": "GPT-4o-Mini",
              "model_name": "gpt-4o-mini",
              "api_key": "sk-YOUR_OPENAI_API_KEY_HERE", // 실제 API 키 입력
              "base_url": null, // 기본 OpenAI URL 사용 시 null
              "max_completion_tokens": 1500,
              "extra_body": {}
            },
            {
              "name": "Claude-3-Opus",
              "model_name": "claude-3-opus-20240229",
              "api_key": "sk-ant-api03-YOUR_ANTHROPIC_API_KEY_HERE", // 실제 API 키 입력
              "base_url": "[https://api.anthropic.com/v1](https://api.anthropic.com/v1)", // 예시 Anthropic URL
              "max_completion_tokens": 1500,
              "extra_body": { // Claude API는 추가 헤더 필요
                "anthropic_version": "2023-06-01"
              }
            },
            // 필요에 따라 다른 모델 추가
          ]
        }
        ```
    * `.gitignore` 파일에 `config.json`이 포함되어 있어 실수로 커밋되는 것을 방지합니다.

## 사용법

### 1. 웹 인터페이스 (권장)

Streamlit 앱을 실행하여 그래픽 인터페이스를 사용합니다.

```bash
streamlit run streamlit_app.py
```

또는 제공된 셸 스크립트를 사용합니다:

```bash
./run.sh
```

웹 UI에서 다음 작업을 수행할 수 있습니다:
* 새 토론 시작
* 과거 토론 기록 보기, 검색, 불러오기, 삭제
* 토론 주제 입력 및 AI 응답 보기
* 메시지 내용 복사
* 현재 토론 상태 스냅샷 생성

### 2. 명령줄 인터페이스

#### 대화형 모드

터미널에서 직접 AI와 토론을 진행합니다. 각 입력마다 3단계 토론 사이클이 실행됩니다.

```bash
python main.py
```

종료하려면 `quit` 또는 `exit`를 입력하거나 `Ctrl+D`를 누릅니다.

#### 토론 기록 검색

키워드 및/또는 날짜 범위로 과거 토론을 검색합니다.

```bash
# 키워드로 검색
python main.py --search --keyword "climate change"

# 날짜 범위로 검색 (YYYY-MM-DD 형식)
python main.py --search --start-date "2025-04-15" --end-date "2025-04-21"

# 키워드와 날짜 범위 모두 사용
python main.py --search --keyword "smart city" --start-date "2025-04-01"
```

검색 결과가 표시된 후 번호를 입력하여 해당 토론의 전체 내용을 볼 수 있습니다.

## 구성 (`config.json`)

`config.json` 파일은 사용할 AI 모델을 정의합니다. 각 모델 객체에는 다음 필드가 포함됩니다:

* `name` (str): UI 및 로그에 표시될 모델의 이름입니다.
* `model_name` (str): API 호출 시 사용될 기술적인 모델 식별자입니다.
* `api_key` (str): 해당 모델 API에 대한 **실제 API 키**입니다.
* `base_url` (str | null): API 엔드포인트 URL입니다. 기본값(예: OpenAI)을 사용하려면 `null`로 설정합니다.
* `max_completion_tokens` (int): 모델이 생성할 최대 토큰 수입니다.
* `extra_body` (dict): API 요청 본문에 추가할 추가 파라미터입니다(예: 특정 API의 버전 헤더).

## 프로젝트 구조

```
llm_cycle/
├── .git                  # Git 리포지토리 메타데이터
├── .gitignore            # Git 추적에서 제외할 파일 목록
├── README.md             # 이 파일
├── config.example.json   # 구성 파일 예시
├── config.json           # 실제 모델 구성 및 API 키 (Git 추적 안 됨)
├── debate_history/       # 저장된 토론 세션 (JSON 파일)
│   └── <session_id>/
│       └── session_<session_id>.json
│       └── snapshot_<timestamp>.json (선택적 스냅샷)
├── main.py               # 핵심 로직 (AI 모델, 기록 관리, 토론 사이클) 및 CLI
├── requirements.txt      # Python 종속성 목록
├── run.sh                # Streamlit 앱 실행 스크립트
└── streamlit_app.py      # Streamlit 웹 인터페이스 코드
```