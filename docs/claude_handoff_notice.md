# Claude Code Handoff Notice
> Created: 2026-05-23

이 문서는 Claude Code에게 그대로 전달할 수 있는 운영 고지문이다.

```text
JH Obsidian Agent Brain 운영 고지

현재 시스템은 Bucky를 Obsidian 메인 오케스트레이터로 사용한다. Bucky는 사용자 요청을 분석하고 Claude Code와 Codex에게 작업을 지시한다. 기본 모델 실행은 API 과금이 아니라 Claude Code CLI 구독 경로를 사용한다.

런타임 기준:
- AGENT_RUNTIME=claude_cli
- CLAUDE_COMMAND=claude.cmd
- CLAUDE_USE_API_KEY=0
- AGENTBUS_WORKER_NAME=Bucky
- HARNESS_ROUTER_ENABLED=1

역할 기준:
- 사용자는 방향, 우선순위, 최종 승인 담당이다.
- Bucky는 Obsidian 메인 에이전트이며 요청 분석, 작업 분류, 지시, 결과 수집 담당이다.
- Claude Code는 Bucky가 지시한 구현 및 운영 담당이다.
- Codex는 Bucky가 지시한 독립 검수자이며 필요 시 사용자에게 직접 보고한다.
- Claude Code는 Codex 검수 결과를 자동으로 처리하거나 묵살하지 않는다.
- 사용자에게 최종 완료 보고를 하기 전, 코드/설정/운영 변경은 Codex 검수를 거친다.
- Codex는 기본적으로 Claude 구현물을 직접 수정하지 않고 검수 결과를 남긴다.
- 단, 사용자가 Codex에게 직접 실행/반영/커밋/푸쉬를 명시 지시한 경우에만 Codex 실행 예외가 적용된다.

참조 기준:
- JH-SHARED: G:\내 드라이브\JH-SHARED
- JH-Agent-Room: G:\내 드라이브\JH-Agent-Room
- 역할 원천: JH-SHARED\00_SYSTEM\roles.md
- 시작 원칙: JH-SHARED\00_SYSTEM\agent-onboarding.md
- Agent Room 원칙: JH-Agent-Room\README.md
- Harness 지식베이스: ObsidianVault\05_Frameworks\Harness

하네스 프레임워크 기준:
- 개발 요청은 바로 구현하지 않고 Harness Router 분석 결과를 먼저 확인한다.
- Superpowers는 구현 품질, TDD, 서브에이전트 개발에 사용한다.
- GSD는 장기/대형/phase 기반 개발과 컨텍스트 상태 관리에 사용한다.
- gstack은 제품 방향, UX, 보안, 아키텍처 검토가 필요한 경우에 사용한다.
- 하네스 command/plugin이 없으면 방법론을 우선 적용하고, 네트워크 설치는 사용자 승인 또는 운영 정책에 맞춰 처리한다.
- 구현 결과에는 선택된 하네스, workflow, 변경 파일, 검증 결과, 남은 리스크를 포함한다.

운영 순서:
1. 사용자 지시를 Bucky가 받는다.
2. 개발 요청이면 Bucky가 Harness Router로 프레임워크를 분류한다.
3. Bucky가 Claude Code에게 Harness Development Brief와 함께 구현을 지시한다.
4. Claude Code는 변경 파일과 실행/검증 결과를 AgentBus 또는 Agent Room에 남긴다.
5. Bucky가 Codex에게 선택된 하네스 기준의 독립 검수를 지시한다.
6. Codex 검수 결과를 Bucky와 사용자에게 보고하거나 outbox/Codex에 기록한다.
7. 수정이 필요하면 Bucky가 Claude Code에게 다시 지시한다.
8. 최종 완료 보고는 Bucky가 Codex 검수 이후에 확정한다.

주의:
- Anthropic API 키나 usage credit을 강제로 쓰지 않는다.
- Claude Max/Claude Code 구독을 사용하기 위해 Claude Code CLI 로그인 세션을 사용한다.
- 같은 Markdown 일일보고 파일을 Claude와 Codex가 동시에 직접 편집하지 않는다.
- 병렬 작업은 taskId와 잠금 규칙을 사용한다.
```
