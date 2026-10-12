# 근거 (dart-theme-agent)

> 사업보고서 원문에서 **근거 문장**을 찾아 테마 소속 기업을 가려내고, 근거가 약하면 **기권**하며, 실제 테마 ETF 구성종목으로 **채점**되는 LangGraph 에이전트. 밑에는 DART·KRX·뉴스를 LLM용 도구로 묶은 **MCP 서버**가 있고, 그 서버의 설계를 실험으로 정했다.

구현 중(2026-10-12 시작). 결과표는 `results/REPORT.md`, 설계·결정·안 하는 것은 `docs/`.

## 한 문장

테마 소속을 **뉴스가 아니라 공시로 증명**하고, **실제 ETF 구성종목으로 채점**했고, **도구 설계가 에이전트 정확도를 얼마나 바꾸는지** 쟀다.

## 구조

```
테마 설명 ─▶ [정의] 밸류체인 단계·검색어 ─▶ [검색] 사업보고서 '사업의 내용' (KURE/bge-m3 + BM25 → RRF)
          ─▶ [검증 ×N 병렬] 핵심|관련|무관|모름 + 근거 문장(원문 그대로, 코드가 대조) ─▶ [조립] ─▶ [인간 게이트]
                                 ▲ langchain-mcp-adapters
                    kr-finance-mcp (FastMCP): search_companies · get_financials · list_filings · get_report_section
                                             · search_report_text · get_prices · get_etf_holdings · search_news
```

- LLM 호출은 **정의·검증 두 노드뿐**. 검색·조립·채점은 결정론.
- 검증 노드의 근거 문장은 코드가 원문과 글자 단위로 대조한다. 바꿔 쓴 근거는 **모름**으로 내린다.
- 숫자 도구의 출력에는 단위·연결/별도·사업연도·출처가 항상 붙는다. 오류 응답에는 "다음에 할 일"이 있다.

## 평가 (분모까지)

| 평가 | 무엇을 재나 | 정답 |
|---|---|---|
| C-1 테마 복원 | 바스켓의 정밀도·재현율·기권률·기권 적중 | 테마 ETF 5개의 실제 구성종목 ∩ 코스피200 |
| C-2 검색 품질 | 임베딩 2종 × {dense, hybrid} → 기업 단위 Recall@10/30 | 같은 정답, LLM 없음 |
| C-3 도구 설계 | 같은 데이터·같은 에이전트, 서버 설계만 다를 때 정확도·토큰·실패 유형 | DART 재무 API로 계산한 100문항 |

## 재현

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .
cp .env.example .env   # OPENDART_API_KEY · KRX_ID/KRX_PW · Gemini(Vertex ADC)
PYTHONPATH=src .venv/bin/python scripts/build_corpus.py        # 사업보고서 수집·파싱
PYTHONPATH=src .venv/bin/python scripts/build_index.py         # 청킹·BM25·임베딩·Chroma
PYTHONPATH=src .venv/bin/python -m dta.eval.run_c2             # 검색 품질
PYTHONPATH=src .venv/bin/python -m dta.eval.run_c1             # 테마 복원
PYTHONPATH=src .venv/bin/python -m dta.eval.questions && PYTHONPATH=src .venv/bin/python -m dta.eval.run_c3   # 도구 설계
PYTHONPATH=src .venv/bin/python -m dta.app.cli theme "원전" --desc "원자력 발전 밸류체인 ..."   # 직접 써 보기
```

MCP 서버를 Claude Code 에 붙이기: `claude mcp add kr-finance -- $PWD/.venv/bin/python -m dta.mcp_server.server`

## 금융 데이터의 함정과 처리 (실측으로 생긴 규칙)

| 함정 | 처리 |
|---|---|
| DART 재무 숫자는 **원 단위 문자열** | 도구 계층에서 억원(`value_eok`)과 원(`value_won`)을 같이 주고 `unit` 필드를 강제(테스트가 막는다) |
| 연결/별도가 섞이면 다른 숫자 | 모든 숫자 도구에 `fs_div`(CFS/OFS) 필수. 지주사·금융사는 연결이 없을 수 있어 오류에 "별도로 다시" 안내 |
| 정정공시: `[첨부정정]` 접수번호에는 **원문 파일이 없다**(DART status 014) | 사업보고서 후보를 늦은 순으로 받아 원문이 있는 첫 접수번호로 폴백(`no_document_file` 사유 기록) |
| 비거래일에 KRX 는 **빈 결과** | 기준일은 마지막 거래일로 고정(2026-10-08; 10-09 한글날·10-10 토). 빈 유니버스는 명시적 오류 |
| pykrx 는 **KRX 로그인** 없이는 거의 아무것도 못 준다 | `.env` KRX_ID/KRX_PW. 받은 CSV 를 캐시해 재현에는 로그인이 필요 없게 |
| 정답 누설 | 테마 설명에 구성종목이 들어가면 테스트가 막는다. 프롬프트 어디에도 종목 목록이 없다 |
| LLM 이 근거를 **바꿔 쓴다** | 근거 문장을 원문과 공백 무시 글자 단위로 대조. 불일치면 `모름` 으로 내리고 사유를 남긴다 |
| 괄호 되풀이 "3조 3,931억원(33,931억원)" | 채점기가 단위 순서가 깨지면 새 값으로 본다(합산 금지) |

## 안 하는 것

종목·시점 추천, 목표가, 수익률 예측. 이 도구는 지수 설계 보조이며 투자 조언이 아니다. 에프앤가이드 등 유료 데이터는 쓰지 않는다(DART·KRX 공개 데이터만).

## 라이선스

MIT
