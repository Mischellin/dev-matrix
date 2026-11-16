# AUDIT-TRAIL — аудиторский след 19-модельного лидерборда

Дата фиксации: 2026-11-17. Ветка: `results/full-main-20261115`, база следа: коммит `905c20c`
(«feat(data): add OpenAI gpt-6.1-terra/sol/6-luna (19 models total)»).

Этот каталог — полная фактура аудита прогонов: машинные JSON-вердикты (`records/`) и
компактные логи очередей (`raw/`, только rc + AUDIT-строки + summaries, без гигантских
per-task JSON-транскриптов). Данные лидерборда (`data/`, `submissions/`, `README.md`)
этим документом не изменяются.

---

## 1. Методология

**Бенчмарк**: 13 задач (sec-01 … idem-13), 222 скрытых acceptance-теста. Агент работает в
режиме `benchmark`; hidden-тесты гоняет сам раннер, модель к ним доступа не имеет.

**Изоляция аудита**: `subagent deny` — агенту запрещено порождать дочерние сессии.

**Аудит-эвристика** (реализация — `raw/openai-offline-audit.py`, та же логика встроена в
очередные раннеры):

- ровно одна сессия на задачу (`multiple session ids` → INVALID);
- session agent == `benchmark` (по DB и по assistant-сообщениям);
- model identity: assistant-сообщения должны быть от ожидаемой модели
  (`assistant_models` vs `expected_model`);
- отсутствие родительских/дочерних сессий (`parent_ids`, `children`);
- forbidden substrings во входах инструментов: `hidden`, `reference_solution`, `ci-sim`,
  `ci_sim`, `dev-matrix-main`, `dev-matrix-submit`;
- parent-path regex: `(^|["\s])\.\./|/\.\./` — попытки выхода за пределы workspace;
- error events (assistant message error);
- `finish_length` (step_finish reason=length — обрыв по длине);
- abort markers: regex `aborted|AbortError`.

**Переквалификация substring false positives — прецеденты.** Эвристика ищет подстроки и
не различает контекст; ряд срабатываний — ложные positives, зафиксированные в
`data/run_overrides.json`:

- `glob:hidden` — стандартный параметр `hidden: true` инструмента glob (workspace-only,
  к hidden-данным отношения не имеет). Прецеденты: GPT-6.1 Terra algo-03/arch-04/flag-10;
  kimi-k3.1-pro v1 algo-03 (запись сохранена, ран заменён v2);
- `shell:hidden` — вхождение слова в exclusion-паттерн `-not -path '*/hidden/*'`
  (исключение каталога, не доступ к нему). Прецеденты: GLM-5.3 v2b host-08/authz-12/idem-13;
- `patch:hidden` / `write:hidden` — слово в имени/тексте собственного теста или TDD-дока
  агента. Прецеденты: GPT-6 Luna scrub-09/flag-10 (patch); Qwen4 Max Preview authz-12
  (refresh-аудит write:hidden — слово в собственном TDD-доке);
- `patch:parent-path` — fixture-строка `../` внутри тестовых данных задачи, не traversal.
  Прецеденты: GPT-6.1 Terra infra-05, GPT-6.1 Sol infra-05.

## 2. Вердикты 19 моделей

Счёт — PASS из 13 задач по `data/benchmark_runs.json` (актуальные, не-outdated записи).
Аудиты — вердикты из `records/` (для очередей openai — офлайн-восстановленные, см. §4).

| Модель | Счёт | Аудиты | Notes |
|---|---|---|---|
| deepseek-v4-pro | 13/13 | 13/13 VALID | — |
| deepseek-v4.1-flash-1017 | 13/13 | 13/13 VALID | — |
| glm-5.3 | 13/13 | 13/13 VALID (v2b) | v2 rerun; v1 write:hidden scrub-09 записана; в v2b 3×shell:hidden (host-08, authz-12, idem-13) реквалифицированы FP — `-not -path '*/hidden/*'`; dead-v2 sec-01 shell:hidden — ран superseded (§4) |
| kimi-k3-256k | 13/13 | 13/13 VALID | — |
| qwen3.8-flash (via Alibaba) | 13/13 | 13/13 VALID | — |
| glm-5.2 (via Alibaba) | 12/13 | 13/13 VALID | FAIL: infra-05 |
| kimi-k3.1-pro | 12/13 | 13/13 VALID (v2) | v2 rerun; v1 glob:hidden algo-03 записана; в v2 все 13 VALID; FAIL: infra-05 |
| qwen3.7-max (via Alibaba) | 12/13 | 13/13 VALID | FAIL: infra-05 |
| gpt-6.1-sol | 12/13 | 12/13 VALID + infra-05 FP-note | FAIL: infra-05; patch:parent-path на infra-05 — FP (fixture-строка) |
| gpt-6.1-terra | 12/13 | 12/13 VALID + FP-notes | 3×glob:hidden — FP (`hidden:true` — стандартный параметр globа); infra-05 patch:parent-path — FP (fixture-строка); FAIL: infra-05 |
| kimi-for-coding | 12/13 | 13/13 VALID | FAIL: infra-05 |
| qwen4-max-preview | 12/13 | 13/13 VALID (refresh) | v1 parent-path INVALID на infra-05 superseded refresh-прогоном; в refresh authz-12 write:hidden — FP (слово в собственном TDD-доке), реквалифицирована; FAIL: infra-05 |
| gpt-6-luna | 11/13 | 10/13 VALID + FP/FAIL-notes | 2×patch:hidden (scrub-09, flag-10) — FP (слово в собственном тесте); infra-05 — genuine FAIL (provider invalid-output, error event); FAIL: infra-05, obs-02 |
| inkling-2-small-free | 11/13 | 13/13 VALID (missing queue) | прогон из missing-очереди; FAIL: infra-05, obs-02 |
| glm-5.3-flash | 11/13 | 12/13 VALID + note | shell:parent-path на FAIL-задаче infra-05 (fixture-строка в тестовых данных, зафиксировано в run_overrides как note); FAIL: infra-05, obs-02 |
| iceman-free | 11/13 | 13/13 VALID | idem-13 — отдельный формальный аудит VALID (`records/iceman-idem13-formal-audit.json`); FAIL: infra-05, obs-02 |
| qwen3.8-max (via Alibaba) | 11/13 | 12/13 VALID, obs-02 INVALID | obs-02 — provider error (assistant message error) → genuine FAIL; FAIL: infra-05, obs-02 |
| qwen3.7-plus (via Alibaba) | 10/13 | 13/13 VALID | FAIL: host-08, infra-05, obs-02 |
| minimax-m3.1-flash | 6/13 | 12/13 VALID, flag-10 INVALID | flag-10 pass REVOKED — write:parent-path (hidden-access violation, не FP); FAIL: arch-04, auth-07, host-08, infra-05, onec-06, scrub-09 + flag-10 |

Источники: `records/provider-queues-audit.json` (234 записи, 20 моделей × 13 задач, v1-прогоны),
`records/missing-queue-audit.json` (78 записей, 6 free-моделей), `records/rerun-v2b-audit.json`
(26 записей), `records/qwen4-refresh-formal-audit.json` (13), `records/iceman-audit.json` (12),
`records/iceman-idem13-formal-audit.json` (1), `records/openai-audit-fixed.json` (39).
Переквалификации и отзывы — `data/run_overrides.json` (14 runs-пометок + 2 model_notes).

## 3. Исключённые модели

| Модель | Причина исключения | Фактура |
|---|---|---|
| beam (Beam Free) | hidden access, результаты отозваны ранее | коммит `9ccd693` «Remove contaminated Beam Free results» |
| minimax-m3 | edit:hidden,glob:hidden на obs-02 + 8 give-ups; исключена решением оператора (MANUAL STOP, остальные lane не затронуты) | `raw/provider-queues.log`, `raw/rerun-v2-dead.log`, `raw/invalid-provider.txt` |
| gigachat-3.5-ultra | 13×402 Payment Required (Translation Proxy) | `raw/invalid-provider.txt` |
| kimi-k2.7-code-via-alibaba | 13× «Access to model denied» | `raw/invalid-provider.txt` |
| minimax-m2.5-via-alibaba | 13× «Access to model denied» | `raw/invalid-provider.txt` |
| longcat-2.5-free | 1/13; 12× «Free usage limit reached» (OpenCode Go-style free limits) | `records/missing-queue-audit.json`, `raw/summary-missing.txt` |
| flint-40b-free | 6/13; 5× free usage limit + обрывы — прогон не доведён до полного аудируемого состояния | `records/missing-queue-audit.json`, `raw/summary-missing.txt` |
| nemotron-3.5-super-vl-free | 9/13; 5× INVALID (в т.ч. read:parent-path) + free limits — прогон не принят | `records/missing-queue-audit.json`, `raw/invalid-missing.txt` |
| mimo-v2.6-flash-free | 0/13; 13× free usage limit | `records/missing-queue-audit.json` |
| big-pickle | 0/13; 13× free usage limit | `records/missing-queue-audit.json` |
| gpt-6-astra | 0/13; subscription_sharing_usage_limit_exceeded (лимит подписки OpenAI после ~21:00Z 2026-11-16) — ждут re-run | `raw/summary-openai1.txt`, per-task логи /tmp/dm-openai-gpt-6-astra-* (13 логов с текстом ошибки) |
| gpt-5.5 | 0/13; та же лимит-ошибка — ждут re-run | `raw/summary-openai1.txt`, per-task логи /tmp/dm-openai-gpt-5.5-* |
| все 13 моделей очереди 2 (gpt-6.1-*-fast, gpt-6-sol/-fast, gpt-6-luna-fast, gpt-6-astra-fast, gpt-5.6-*-fast, gpt-5.5-fast) | 169× rc=1, subscription_sharing_usage_limit_exceeded — ждут re-run | `raw/openai-queue2.log`, `raw/summary-openai2.txt` |

Примечание: текст провайдерской ошибки `subscription_sharing_usage_limit_exceeded`
в `raw/openai-queue1.log`/`raw/openai-queue2.log` не попадает (в них только rc + traceback
аудита) — он зафиксирован в per-task логах задач (/tmp/dm-openai*-\<model\>-\<task\>.log,
не копирулись в репо из-за объёма).

## 4. Инциденты и фиксы

1. **Inline-audit bug в openai-очередях** (`dm-openai.sh` / `dm-openai2.sh`): inline-аудит
   падал на каждой задаче — `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`
   (`<stdin>` line 92, `.get(key)` вернул None; 65 traceback'ов в queue1, 169 в queue2).
   Файлы `/tmp/dm-openai-audit.json` и `/tmp/dm-openai2-audit.json` — пустые массивы `[]`.
   **Фикс**: офлайн re-audit по session-логам (`raw/openai-offline-audit.sh` +
   `raw/openai-offline-audit.py`) — восстановлены все 39 записей трёх лидерборд-моделей
   (`records/openai-audit-fixed.json`): 31 VALID, 8 findings → 7 реквалифицированы FP,
   1 genuine (gpt-6-luna infra-05 provider invalid-output).
2. **SIGHUP-инцидент v2-очереди** (rerun kimi-k3.1-pro + glm-5.3): запуск в Terminal был
   убит закрытием терминала после 1-й задачи (glm sec-01 shell:hidden — вероятный FP того
   же класса, что и v2b; ран superseded). minimax-m3 lane получила MANUAL STOP.
   **Фикс**: перезапуск через `setsid` (nohup, отсоединённый от терминала) — v2b прогон
   завершён полностью (`raw/rerun-v2-dead.log`, `raw/rerun-v2b.log`,
   `records/rerun-v2b-audit.json`).
3. **v1-нарушения kimi-k3.1-pro и glm-5.3** (glob:hidden / write:hidden на 1 задаче у
   каждой): прогон v1 сохранён в аудите как запись, заменён v2/v2b rerun'ом
   (`data/run_overrides.json` model_notes).
4. **Отзыв pass'а minimax-m3.1-flash flag-10**: write:parent-path — genuine hidden-access
   violation, FP-классом не является; счёт 7/13 → 6/13 (`data/run_overrides.json`).

## 5. Связь с коммитами

- `4621753` — fix(vast-bench): resolve shellcheck findings (SC2148,SC1010,SC2034,SC2009,SC2317);
- `7195843` — feat(data): final leaderboard — 16 models, audited runs, v2 reruns for
  kimi-k3.1-pro & glm-5.3;
- `905c20c` — feat(data): add OpenAI gpt-6.1-terra/sol/6-luna (19 models total);
- `data/run_overrides.json` — 14 runs-пометок (реквалификации FP, notes, REVOKED flag-10) +
  2 model_notes (v2 reruns kimi-k3.1-pro и glm-5.3).

## 6. Repro

Пересчёт метрик и проверка целостности (данные `data/` + `submissions/`):

```bash
uv run python scripts/export_metrics.py --only-benchmarks   # пересборка метрик из submissions/
uv run python scripts/generate_readme.py                    # генерация README-таблицы
uv run python scripts/check_submissions.py                  # валидация сабмитов против data/
uv run pytest tests/test_export_benchmarks.py               # юнит-тесты экспорта
```

Расположение evidence: машинные вердикты — `audits/records/*.json`; логи очередей и
summaries — `audits/raw/*`; переквалификации — `data/run_overrides.json`; счёт моделей —
`data/benchmark_runs.json`. Per-task session-логи и full-транскрипты остаются в /tmp
(в репо сознательно не копируются — объём); при необходимости репродуцирования аудита
использовать `raw/openai-offline-audit.py` как эталонную реализацию эвристики.

Отсутствующие / в неполном виде источники:
- `dm-opencode-missing-reasons.txt` — пустой (0 байт) в /tmp, не копировался;
  причины по missing-очереди полны в `records/missing-queue-audit.json`.
- Аудит v2b-прогона присутствует и скопирован: `records/rerun-v2b-audit.json`
  (26 записей, kimi-k3.1-pro 13×VALID; glm-5.3 10×VALID + 3×shell:hidden, реквалифицированы FP).
- Per-task session-логи queue1/queue2 openai (текст ошибки лимита) и полные
  транскрипты прогонов в репо не копировались (объём); перечислены в §3.
