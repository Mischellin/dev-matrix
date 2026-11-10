# INFRA: Мутационный валидатор политик безопасности и топологии Kubernetes

## Проблема
Платформенная инфраструктура кластера Kubernetes требует строгого соблюдения стандартов безопасности (Pod Security Standards / Restricted profile) и высокой доступности (HA) перед допуском рабочих нагрузок в кластер. Текущая заготовка модуля `k8s_admission.mutator` выполняет лишь базовую проверку структуры манифеста, но пропускает критические уязвимости и не нормализует квоты ресурсов и топологические ограничения.

## Требования к `mutate_and_validate(manifest: dict[str, Any]) -> dict[str, Any]`

Функция принимает словарь манифеста Kubernetes (`Pod` или `Deployment`) и возвращает нормализованную, обогащенную копию манифеста либо вызывает `AdmissionPolicyViolation` при недопустимых нарушениях. Исходный словарь `manifest` не должен мутировать при ошибках. Манифесты других видов (`Service`, `ConfigMap` и т. д.) возвращаются неизменными (глубокая копия).

### 1. Безопасность окружения (Pod Security Standards):
- **Запрет привилегированных пространств имен:** Если `hostNetwork`, `hostPID` или `hostIPC` установлены в `True`, выбросить `AdmissionPolicyViolation("Host namespaces are forbidden")`.
- **Запрет небезопасных точек монтирования hostPath:** Любой том `hostPath`, монтирующий корень (`/`), системные директории (`/etc`, `/proc`, `/sys`, `/var/run`) или сокет докера (`/var/run/docker.sock`), должен отклоняться ошибкой `AdmissionPolicyViolation`. Безопасные типы томов (`emptyDir`, `configMap`, `secret`, `persistentVolumeClaim`) разрешены.
- **Pod-level `securityContext`:**
  - Обязательно установить `runAsNonRoot: True`.
  - Если явно задан `runAsUser: 0`, выбросить `AdmissionPolicyViolation("Root user (UID 0) is forbidden")`.
- **Container-level `securityContext`:**
  - Для каждого контейнера в `containers` и `initContainers`:
    - `readOnlyRootFilesystem: True` (установить, если не задано).
    - `allowPrivilegeEscalation: False` (установить, если не задано).
    - `capabilities.drop`: список обязан содержать `"ALL"`.

### 2. Квоты и единицы измерения ресурсов (Resource Management):
Для каждого контейнера (`containers` и `initContainers`):
- Если блок `resources` или отдельные поля отсутствуют, подставить значения по умолчанию:
  - `requests`: `{"cpu": "100m", "memory": "128Mi"}`
  - `limits`: `{"cpu": "500m", "memory": "512Mi"}`
- **Парсинг и валидация единиц:**
  - CPU: миллипотоки (`"100m"` -> 100) или целые/дробные ядра (`"1"` -> 1000, `"0.5"` -> 500).
  - Память: бинарные (`Ki`, `Mi`, `Gi`, `Ti` со степенями 1024) и десятичные (`k`/`K`, `M`, `G`, `T` со степенями 1000) суффиксы, либо сырые байты.
- **Проверка потолка:**
  - Если `limit < request` по CPU или памяти, выбросить `AdmissionPolicyViolation`.
  - Значения запросов и лимитов должны быть строго больше 0.

### 3. Высокая доступность и Topology Spread:
- Для ресурсов `Deployment` при `spec.replicas >= 2`:
  - В `spec.template.spec` проверить наличие правила в `topologySpreadConstraints` по ключу `topologyKey: "topology.kubernetes.io/zone"`.
  - Если такое правило отсутствует, добавить:
    ```yaml
    maxSkew: 1
    topologyKey: "topology.kubernetes.io/zone"
    whenUnsatisfiable: "DoNotSchedule"
    labelSelector:
      matchLabels: <копия spec.selector.matchLabels>
    ```

### 4. Метаданные:
- В `metadata.annotations` манифеста (а для `Deployment` — также и в `spec.template.metadata.annotations`) добавить аннотацию:
  `"policy.dev-matrix.io/admitted": "true"`.

## Критерий готовности
Все базовые и приемочные тесты запускаются через `pytest tests/` и успешно проходят.
