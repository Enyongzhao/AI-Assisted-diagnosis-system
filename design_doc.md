# Design Doc: AI-Assisted Clinical Diagnosis Report System

**版本：** v1.0  
**作者：** Ethan Zhao  
**状态：** Draft

---

## 1. 项目背景

### 系统描述

本系统是一个面向医疗机构的 AI 辅助临床诊断报告平台。Clinician 输入患者基本信息与症状描述，系统调用 LLM 生成结构化初步分析报告；Clinician 审阅后填写最终诊断意见，系统将 LLM 报告与医生意见合并生成完整 PDF 报告，供患者查阅下载。

### 用户角色

| 角色 | 说明 |
|---|---|
| **Admin** | 管理用户账户、查看全部诊断记录、系统配置 |
| **Clinician** | 填写患者信息 → 触发 LLM 生成报告 → 填写诊断意见 → 生成 PDF |
| **Client（患者）** | 查看本人完整诊断报告（LLM 分析 + 医生意见），下载 PDF |

### 解决的核心问题

1. **LLM 生成耗时**：LLM API 调用需 3–10 秒，同步接口会阻塞用户；通过异步架构让 Clinician 提交后立即返回，后台处理完毕后前端轮询获取结果。
2. **多 LLM 提供商**：需同时支持 Claude 和 OpenAI，两者 API 格式不同；通过 Adapter 模式统一内部接口，业务层无感知切换。
3. **报告格式标准化**：LLM 输出为非结构化文本，需与医生意见合并生成格式统一的 PDF 报告。
4. **重复提交**：同一患者短时间内被重复提交会浪费 LLM token 并产生冗余记录；引入检测机制区分硬错误与软警告。
5. **基础设施一致性**：本地开发与生产环境差异大；Docker Compose 保证本地一致，Terraform 管理 AWS 资源。

---

## 2. 核心功能列表

- [x] JWT 认证 + 基于角色的权限控制（RBAC），3 个用户角色
- [x] 12+ RESTful API 端点，支持诊断任务的完整 CRUD
- [x] 患者信息录入：结构化字段（年龄、性别、体温等）+ 自由文本症状描述，两者组合构建 LLM prompt
- [x] 异步 LLM 报告生成：Clinician 提交后立即返回 job ID，Celery/Lambda 后台调用 LLM，前端轮询结果
- [x] LLM Adapter 模式：统一 Claude / OpenAI 两种 API 格式，业务层调用单一接口
- [x] Clinician 填写自由文本诊断意见，与 LLM 报告合并
- [x] PDF 报告生成：包含患者信息、LLM 分析内容、医生诊断意见，支持 Clinician 和 Client 下载
- [x] 重复提交检测：同一患者 1h 内重复提交 → 400 Hard Error；超过 1h → 200 + Warning
- [x] PostgreSQL 关系型数据库建模，含用户、患者、诊断任务、LLM 结果、医生意见五张核心表
- [x] 本地开发：Docker Compose（API + Celery + Redis + PostgreSQL）
- [x] AWS 生产部署：API Gateway + Lambda + SQS + RDS + S3，Terraform 一键拉起
- [x] Prometheus + Grafana 监控队列深度、LLM 调用延迟、错误率
- [x] SQS Dead Letter Queue 兜底失败任务，写库告警
- [x] pytest 单元测试，mock 所有外部 LLM/S3 调用，90%+ 覆盖率
- [x] 代码分层：Controller（Django views）→ Service → Repository

---

## 3. 技术栈

### 后端

| 技术 | 选型理由 |
|---|---|
| **Python 3.11** | LLM SDK（anthropic、openai）均原生支持 Python，生态成熟 |
| **Django 4.2** | 内置 ORM、Admin、Auth 体系，加速开发；成熟的安全机制 |
| **Django REST Framework** | Serializer、ViewSet、Permission Class，快速实现规范 RESTful API |
| **PostgreSQL 15** | 支持 JSONB 存储 LLM 原始输出，事务性强，适合医疗数据一致性要求 |
| **Celery 5 + Redis** | 本地异步任务调度，支持任务重试、优先级队列，开发调试方便 |
| **WeasyPrint** | 纯 Python HTML→PDF 转换，支持中文字体，无需外部进程 |

### 云 & 基础设施

| 技术 | 选型理由 |
|---|---|
| **AWS SQS** | 生产异步消息队列，托管服务免运维，与 Lambda 原生集成 |
| **AWS Lambda** | 无服务器 Worker，按调用计费，LLM 任务量弹性伸缩 |
| **AWS RDS (PostgreSQL)** | 托管数据库，自动备份、多 AZ 高可用 |
| **AWS S3** | 存储生成的 PDF 报告，Pre-signed URL 供用户直接下载 |
| **AWS API Gateway** | 统一入口，处理限流、HTTPS 终结 |
| **Terraform** | 基础设施即代码，版本化管理，避免手动配置漂移 |
| **Docker + Docker Compose** | 本地容器化，保证与生产 Python 版本、依赖版本一致 |

### 可观测性 & 测试

| 技术 | 选型理由 |
|---|---|
| **Prometheus** | Pull-based 指标采集，django-prometheus 快速集成 |
| **Grafana** | 可视化仪表盘，支持告警规则配置 |
| **pytest + pytest-django** | Python 生态标准测试框架，Fixture 机制灵活 |
| **unittest.mock** | 标准库 Mock，patch 外部 LLM API 调用，不产生真实费用 |

---

## 4. API 设计

### 基础路径

```
/api/v1/
```

### 认证

所有受保护接口需在 Header 中携带：

```
Authorization: Bearer <access_token>
```

---

### 4.1 认证模块

#### `POST /api/v1/auth/login/`

**Request:**
```json
{
  "username": "dr_smith",
  "password": "securepassword123"
}
```

**Response 200:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 42,
    "username": "dr_smith",
    "role": "clinician"
  }
}
```

**Response 401:**
```json
{ "detail": "Invalid credentials" }
```

---

#### `POST /api/v1/auth/refresh/`

**Request:**
```json
{ "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

**Response 200:**
```json
{ "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

---

### 4.2 患者管理模块

#### `POST /api/v1/patients/`

**权限：** Clinician, Admin

**Request:**
```json
{
  "name": "John Smith",
  "date_of_birth": "1985-03-22",
  "gender": "male",
  "contact_email": "john@example.com"
}
```

**Response 201:**
```json
{
  "id": 123,
  "name": "John Smith",
  "date_of_birth": "1985-03-22",
  "gender": "male",
  "contact_email": "john@example.com",
  "created_at": "2025-05-10T08:00:00Z"
}
```

#### `GET /api/v1/patients/{id}/` · `PUT /api/v1/patients/{id}/` · `DELETE /api/v1/patients/{id}/`

标准 CRUD，字段同上。DELETE 为软删除，Admin only。

---

### 4.3 诊断任务模块（核心）

#### `POST /api/v1/diagnosis/`

**用途：** Clinician 提交患者信息，触发异步 LLM 报告生成  
**权限：** Clinician only

**Request:**
```json
{
  "patient_id": 123,
  "structured_data": {
    "age": 39,
    "gender": "male",
    "temperature": 38.5,
    "blood_pressure": "130/85",
    "heart_rate": 92,
    "symptoms": ["cough", "fatigue", "shortness_of_breath"],
    "duration_days": 5,
    "existing_conditions": ["hypertension"]
  },
  "free_text": "Patient reports worsening cough over 5 days, mild fever, and difficulty breathing when climbing stairs. No recent travel history."
}
```

**Response 202（已接受，异步处理中）：**
```json
{
  "diagnosis_id": "a3f9b2c1-4e5d-4f6a-b7c8-d9e0f1a2b3c4",
  "status": "pending",
  "submitted_at": "2025-05-10T08:30:00Z",
  "message": "LLM report generation in progress. Poll /api/v1/diagnosis/{id}/ for result."
}
```

**Response 400（1h 内同一患者重复提交 — Hard Error）：**
```json
{
  "error": "DUPLICATE_SUBMISSION",
  "message": "A diagnosis for this patient was submitted within the last hour.",
  "original_diagnosis_id": "b1c2d3e4-...",
  "original_submitted_at": "2025-05-10T07:45:00Z"
}
```

**Response 202 + Warning（超过 1h 的重复提交 — Soft Warning）：**
```json
{
  "diagnosis_id": "new-uuid",
  "status": "pending",
  "warning": "POSSIBLE_DUPLICATE",
  "warning_message": "A recent diagnosis exists for this patient. Proceeding.",
  "previous_diagnosis_id": "old-uuid"
}
```

---

#### `GET /api/v1/diagnosis/{diagnosis_id}/`

**用途：** 轮询任务状态及 LLM 报告内容

**Response 200（处理中）：**
```json
{
  "diagnosis_id": "a3f9b2c1-...",
  "status": "processing",
  "submitted_at": "2025-05-10T08:30:00Z",
  "llm_report": null,
  "doctor_opinion": null
}
```

**Response 200（LLM 完成，等待医生填写意见）：**
```json
{
  "diagnosis_id": "a3f9b2c1-...",
  "status": "awaiting_doctor_input",
  "submitted_at": "2025-05-10T08:30:00Z",
  "llm_report": {
    "summary": "Patient presents with symptoms consistent with lower respiratory tract infection. Elevated temperature (38.5°C), tachycardia (HR 92), and progressive dyspnea suggest possible community-acquired pneumonia.",
    "differential_diagnosis": ["Community-acquired pneumonia", "Acute bronchitis", "COVID-19"],
    "recommended_investigations": ["Chest X-ray", "Full blood count", "CRP", "COVID-19 PCR"],
    "risk_factors": ["Hypertension", "5-day symptom duration"],
    "generated_by": "claude-sonnet-4-6",
    "generated_at": "2025-05-10T08:30:08Z"
  },
  "doctor_opinion": null
}
```

**Response 200（完成）：**
```json
{
  "diagnosis_id": "a3f9b2c1-...",
  "status": "completed",
  "llm_report": { "...": "同上" },
  "doctor_opinion": {
    "text": "Consistent with CAP. Initiating amoxicillin 500mg TID for 7 days. Follow-up in 5 days.",
    "submitted_by": "dr_smith",
    "submitted_at": "2025-05-10T09:15:00Z"
  },
  "pdf_url": "https://s3.amazonaws.com/bucket/reports/a3f9b2c1-.../report.pdf"
}
```

---

#### `PATCH /api/v1/diagnosis/{diagnosis_id}/opinion/`

**用途：** Clinician 填写诊断意见，触发 PDF 生成  
**权限：** 仅提交该任务的 Clinician

**Request:**
```json
{
  "text": "Consistent with CAP. Initiating amoxicillin 500mg TID for 7 days. Follow-up in 5 days."
}
```

**Response 200:**
```json
{
  "diagnosis_id": "a3f9b2c1-...",
  "status": "generating_pdf",
  "message": "Opinion saved. PDF generation in progress."
}
```

---

#### `GET /api/v1/diagnosis/{diagnosis_id}/report/`

**用途：** 获取 PDF 下载链接（Pre-signed URL，有效期 15 分钟）  
**权限：** Clinician（仅自己提交的）、Client（仅本人记录）、Admin（全部）

**Response 200:**
```json
{
  "diagnosis_id": "a3f9b2c1-...",
  "pdf_url": "https://s3.amazonaws.com/bucket/reports/a3f9b2c1-.../report.pdf?X-Amz-Expires=900&...",
  "expires_at": "2025-05-10T09:30:00Z"
}
```

**Response 403:**
```json
{ "detail": "You do not have permission to access this report." }
```

---

#### `GET /api/v1/diagnosis/`

**用途：** 列出诊断任务（Clinician 只看自己的，Client 只看本人的，Admin 看全部）

**Query Params:** `?status=completed&patient_id=123&page=1&page_size=20`

**Response 200:**
```json
{
  "count": 32,
  "next": "/api/v1/diagnosis/?page=2",
  "previous": null,
  "results": [
    {
      "diagnosis_id": "a3f9b2c1-...",
      "patient_id": 123,
      "patient_name": "John Smith",
      "status": "completed",
      "submitted_at": "2025-05-10T08:30:00Z"
    }
  ]
}
```

---

### 4.4 用户管理模块（Admin only）

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/v1/users/` | 列出所有用户 |
| `POST` | `/api/v1/users/` | 创建用户并分配角色 |
| `PUT` | `/api/v1/users/{id}/` | 修改用户信息/角色 |
| `DELETE` | `/api/v1/users/{id}/` | 停用用户账户（软删除） |

---

## 5. 数据库设计

### 5.1 表结构

#### `users` 表

```sql
CREATE TABLE users (
    id          SERIAL      PRIMARY KEY,
    username    VARCHAR(150) NOT NULL UNIQUE,
    email       VARCHAR(254) NOT NULL UNIQUE,
    password    VARCHAR(128) NOT NULL,              -- bcrypt hash
    role        VARCHAR(20)  NOT NULL
                CHECK (role IN ('admin', 'clinician', 'client')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

---

#### `patients` 表

```sql
CREATE TABLE patients (
    id            SERIAL      PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    date_of_birth DATE         NOT NULL,
    gender        VARCHAR(10)  NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    contact_email VARCHAR(254),
    linked_user   INTEGER      REFERENCES users(id),   -- 关联 Client 账户（可选）
    created_by    INTEGER      NOT NULL REFERENCES users(id),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_deleted    BOOLEAN      NOT NULL DEFAULT FALSE
);
```

---

#### `diagnosis_jobs` 表

```sql
CREATE TABLE diagnosis_jobs (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id        INTEGER      NOT NULL REFERENCES patients(id),
    submitted_by      INTEGER      NOT NULL REFERENCES users(id),
    -- 结构化输入（固定字段）
    age               INTEGER,
    gender            VARCHAR(10),
    temperature       NUMERIC(4,1),
    blood_pressure    VARCHAR(20),
    heart_rate        INTEGER,
    symptoms          TEXT[],                           -- PostgreSQL array
    duration_days     INTEGER,
    existing_conditions TEXT[],
    -- 自由文本输入
    free_text         TEXT,
    -- 状态
    status            VARCHAR(30)  NOT NULL DEFAULT 'pending'
                      CHECK (status IN (
                          'pending', 'processing', 'awaiting_doctor_input',
                          'generating_pdf', 'completed', 'failed'
                      )),
    has_warning       BOOLEAN      NOT NULL DEFAULT FALSE,
    warning_type      VARCHAR(50),
    -- 时间戳
    submitted_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ,
    is_deleted        BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_diagnosis_jobs_patient  ON diagnosis_jobs(patient_id, submitted_at);
CREATE INDEX idx_diagnosis_jobs_status   ON diagnosis_jobs(status);
CREATE INDEX idx_diagnosis_jobs_submitter ON diagnosis_jobs(submitted_by);
```

---

#### `llm_reports` 表

```sql
CREATE TABLE llm_reports (
    id                  SERIAL      PRIMARY KEY,
    diagnosis_id        UUID        NOT NULL UNIQUE REFERENCES diagnosis_jobs(id),
    llm_provider        VARCHAR(20) NOT NULL CHECK (llm_provider IN ('claude', 'openai')),
    llm_model           VARCHAR(100) NOT NULL,          -- e.g. 'claude-sonnet-4-6'
    prompt_tokens       INTEGER     NOT NULL,
    completion_tokens   INTEGER     NOT NULL,
    -- 结构化输出（LLM 返回 JSON，解析后存储）
    summary             TEXT        NOT NULL,
    differential_diagnosis  TEXT[]  NOT NULL,
    recommended_investigations TEXT[] NOT NULL,
    risk_factors        TEXT[]      NOT NULL,
    -- 原始输出备份
    raw_response        JSONB       NOT NULL,
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

#### `doctor_opinions` 表

```sql
CREATE TABLE doctor_opinions (
    id              SERIAL      PRIMARY KEY,
    diagnosis_id    UUID        NOT NULL UNIQUE REFERENCES diagnosis_jobs(id),
    submitted_by    INTEGER     NOT NULL REFERENCES users(id),
    text            TEXT        NOT NULL,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

#### `reports` 表（PDF 存储记录）

```sql
CREATE TABLE reports (
    id              SERIAL      PRIMARY KEY,
    diagnosis_id    UUID        NOT NULL UNIQUE REFERENCES diagnosis_jobs(id),
    s3_key          VARCHAR(512) NOT NULL,             -- S3 object key
    file_size_bytes INTEGER     NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

#### `job_errors` 表（DLQ 失败记录）

```sql
CREATE TABLE job_errors (
    id              SERIAL      PRIMARY KEY,
    diagnosis_id    UUID        NOT NULL REFERENCES diagnosis_jobs(id),
    error_type      VARCHAR(100) NOT NULL,
    error_message   TEXT        NOT NULL,
    sqs_message_id  VARCHAR(256),
    retry_count     INTEGER     NOT NULL DEFAULT 0,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 5.2 表关系

```
users ──< diagnosis_jobs  (submitted_by)
users ──< patients        (created_by)
users ──── patients       (linked_user, 可选，关联 Client 账户)
patients ──< diagnosis_jobs (patient_id)
diagnosis_jobs ──── llm_reports      (1:1)
diagnosis_jobs ──── doctor_opinions  (1:1)
diagnosis_jobs ──── reports          (1:1)
diagnosis_jobs ──< job_errors        (1:N)
```

---

## 6. 异步架构

### 整体流程

```
┌──────────────┐  POST /api/v1/diagnosis/   ┌──────────────────┐
│  Clinician   │ ─────────────────────────► │   Django API     │
│   Browser    │ ◄───────────────────────── │   (DRF View)     │
│              │   202 + diagnosis_id        └────────┬─────────┘
│              │                                      │
│  轮询状态     │   GET /diagnosis/{id}/               │ 1. 写 diagnosis_jobs (status=pending)
│  pending →   │ ─────────────────────────►           │ 2. 发送消息到队列
│  awaiting_   │ ◄─────────────────────────           │
│  doctor_input│   返回 llm_report 内容     ┌────────▼─────────┐
│              │                            │   Message Queue   │
│  填写意见     │  PATCH /opinion/           │  本地: Redis      │
│              │ ─────────────────────────► │  生产: AWS SQS    │
│              │ ◄───────────────────────── └────────┬─────────┘
│              │   200 + status=generating_pdf        │ consume
└──────────────┘                            ┌────────▼─────────┐
                                            │      Worker       │
                                            │  本地: Celery     │
                                            │  生产: Lambda     │
                                            │                   │
                                            │ 1. 构建 prompt    │
                                            │    (结构化字段 +  │
                                            │     自由文本)     │
                                            │ 2. 调用 LLM API   │
                                            │    (Adapter 层)   │
                                            │ 3. 解析 JSON 响应 │
                                            │ 4. 写入 llm_      │
                                            │    reports 表     │
                                            │ 5. 更新 status=   │
                                            │    awaiting_      │
                                            │    doctor_input   │
                                            └────────┬─────────┘
                                                     │
                              ┌──────────────────────┤ Clinician 提交意见后
                              │                      │ 触发第二个异步任务
                              ▼                      │
                    ┌─────────────────┐   ┌──────────▼─────────┐
                    │  SQS DLQ        │   │  PDF Worker         │
                    │  失败消息兜底    │   │  1. 读取 llm_report │
                    │  写 job_errors  │   │  2. 读取 opinion    │
                    │  触发 SNS 告警  │   │  3. 渲染 HTML 模板  │
                    └─────────────────┘   │  4. WeasyPrint→PDF  │
                                          │  5. 上传 S3         │
                                          │  6. 写 reports 表   │
                                          │  7. status=completed│
                                          └─────────────────────┘
```

### Celery Task 定义

```python
# tasks/llm_task.py
@app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_llm_report(self, diagnosis_id: str):
    try:
        job = DiagnosisRepository.get_by_id(diagnosis_id)
        DiagnosisRepository.update_status(diagnosis_id, "processing")

        prompt = PromptBuilder.build(job.structured_data, job.free_text)
        report  = LLMAdapter.generate(prompt)   # Adapter 统一接口

        LLMReportRepository.create(diagnosis_id, report)
        DiagnosisRepository.update_status(diagnosis_id, "awaiting_doctor_input")
    except Exception as exc:
        DiagnosisRepository.update_status(diagnosis_id, "failed")
        raise self.retry(exc=exc)


# tasks/pdf_task.py
@app.task(bind=True, max_retries=3, default_retry_delay=10)
def generate_pdf_report(self, diagnosis_id: str):
    try:
        DiagnosisRepository.update_status(diagnosis_id, "generating_pdf")

        job     = DiagnosisRepository.get_by_id(diagnosis_id)
        report  = LLMReportRepository.get_by_diagnosis(diagnosis_id)
        opinion = DoctorOpinionRepository.get_by_diagnosis(diagnosis_id)

        pdf_bytes = PDFService.render(job, report, opinion)
        s3_key    = S3Adapter.upload(pdf_bytes, f"reports/{diagnosis_id}/report.pdf")

        ReportRepository.create(diagnosis_id, s3_key, len(pdf_bytes))
        DiagnosisRepository.update_status(diagnosis_id, "completed")
    except Exception as exc:
        DiagnosisRepository.update_status(diagnosis_id, "failed")
        raise self.retry(exc=exc)
```

### LLM Prompt 构建

```python
# services/prompt_builder.py
class PromptBuilder:
    @staticmethod
    def build(structured: dict, free_text: str) -> str:
        return f"""You are a clinical decision support assistant.
Analyze the following patient information and provide a structured report in JSON format.

Patient Information:
- Age: {structured['age']}
- Gender: {structured['gender']}
- Temperature: {structured['temperature']}°C
- Blood Pressure: {structured['blood_pressure']}
- Heart Rate: {structured['heart_rate']} bpm
- Symptoms: {', '.join(structured['symptoms'])}
- Duration: {structured['duration_days']} days
- Existing Conditions: {', '.join(structured['existing_conditions'])}

Clinical Notes from Doctor:
{free_text}

Return ONLY a JSON object with these fields:
{{
  "summary": "...",
  "differential_diagnosis": ["...", "..."],
  "recommended_investigations": ["...", "..."],
  "risk_factors": ["...", "..."]
}}"""
```

### LLM Adapter

```python
# adapters/llm_adapter.py
class LLMAdapter:
    """统一 Claude 和 OpenAI 接口，业务层只调用 generate()"""

    @staticmethod
    def generate(prompt: str) -> dict:
        provider = settings.LLM_PROVIDER
        if provider == "claude":
            raw = ClaudeAdapter().call(prompt)
        elif provider == "openai":
            raw = OpenAIAdapter().call(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
        return json.loads(raw)   # 解析 JSON，统一返回 dict


class ClaudeAdapter:
    def call(self, prompt: str) -> str:
        client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class OpenAIAdapter:
    def call(self, prompt: str) -> str:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

---

## 7. 部署架构

### 7.1 本地开发（Docker Compose）

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/diagnosis_db
      - REDIS_URL=redis://redis:6379/0
      - LLM_PROVIDER=claude
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    depends_on: [db, redis]

  celery_worker:
    build: .
    command: celery -A config worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/diagnosis_db
      - REDIS_URL=redis://redis:6379/0
      - LLM_PROVIDER=claude
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    depends_on: [db, redis]

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: diagnosis_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes: ["pg_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine

  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml"]

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]

volumes:
  pg_data:
```

**启动命令：**
```bash
docker compose up --build
```

---

### 7.2 AWS 生产部署

```
Internet
    │
    ▼
API Gateway (HTTPS + JWT 验证 + 限流)
    │
    ▼
Django API（ECS Fargate）
    │
    ├──► RDS PostgreSQL（Multi-AZ）
    │
    ├──► S3（PDF 报告存储，Pre-signed URL 下载）
    │
    └──► SQS Queue（LLM 任务 & PDF 任务）
              │
              ▼
         Lambda Function（LLM Worker）
              │
              ├──► Claude / OpenAI API
              └──► RDS PostgreSQL（写入 llm_reports）

         Lambda Function（PDF Worker）
              │
              ├──► RDS PostgreSQL（读取报告数据）
              ├──► WeasyPrint 渲染 PDF
              └──► S3（上传 PDF）

         SQS DLQ
              │
              ▼
         Lambda（DLQ 处理：写 job_errors + SNS 告警）
```

**Terraform 关键资源：**

```hcl
# main.tf
module "sqs_llm" {
  source             = "./modules/sqs"
  queue_name         = "llm-report-jobs"
  visibility_timeout = 120
  max_receive_count  = 3
  dlq_name           = "llm-report-jobs-dlq"
}

module "sqs_pdf" {
  source             = "./modules/sqs"
  queue_name         = "pdf-generation-jobs"
  visibility_timeout = 60
  max_receive_count  = 3
  dlq_name           = "pdf-generation-jobs-dlq"
}

module "lambda_llm" {
  source        = "./modules/lambda"
  function_name = "llm-report-worker"
  runtime       = "python3.11"
  handler       = "llm_worker.handler"
  sqs_arn       = module.sqs_llm.queue_arn
  timeout       = 90
  env_vars = {
    DB_SECRET_ARN = aws_secretsmanager_secret.db.arn
    LLM_PROVIDER  = "claude"
    CLAUDE_API_KEY_SECRET_ARN = aws_secretsmanager_secret.claude.arn
  }
}

module "lambda_pdf" {
  source        = "./modules/lambda"
  function_name = "pdf-generation-worker"
  runtime       = "python3.11"
  handler       = "pdf_worker.handler"
  sqs_arn       = module.sqs_pdf.queue_arn
  timeout       = 60
}

module "rds" {
  source         = "./modules/rds"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  multi_az       = true
}
```

**一键部署：**
```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## 8. 监控

### 8.1 Prometheus 指标

| 指标名 | 类型 | 说明 |
|---|---|---|
| `diagnosis_jobs_submitted_total` | Counter | 累计提交任务数 |
| `diagnosis_jobs_completed_total` | Counter | 累计完成任务数（label: status） |
| `llm_report_duration_seconds` | Histogram | LLM 调用耗时（bucket: 2s, 5s, 10s, 30s） |
| `pdf_generation_duration_seconds` | Histogram | PDF 生成耗时 |
| `llm_api_tokens_total` | Counter | LLM token 消耗（label: provider, type=prompt/completion） |
| `sqs_queue_depth` | Gauge | SQS 队列待处理消息数 |
| `dlq_message_count` | Gauge | DLQ 中失败消息数（> 0 即告警） |
| `django_http_requests_total` | Counter | HTTP 请求数（label: method, endpoint, status） |

**Prometheus 配置：**
```yaml
scrape_configs:
  - job_name: 'django-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics

  - job_name: 'cloudwatch'
    static_configs:
      - targets: ['cloudwatch-exporter:9106']
```

---

### 8.2 Grafana Dashboard

**Dashboard 1: System Health**
- 面板 1：每分钟任务提交量
- 面板 2：任务完成率（completed / submitted，过去 1h）
- 面板 3：SQS 队列深度折线（告警线：> 50）
- 面板 4：DLQ 消息数（> 0 即红色告警）

**Dashboard 2: LLM Performance**
- 面板 1：LLM 调用耗时 p50 / p95 / p99
- 面板 2：Token 消耗趋势（Claude vs OpenAI 对比）
- 面板 3：LLM 失败率趋势

**Dashboard 3: API Traffic**
- 面板 1：各 endpoint 请求量
- 面板 2：4xx / 5xx 错误率
- 面板 3：API 响应时间 p95

**告警规则：**
```
- DLQ 消息数 > 0 持续 1 分钟  → Slack #alerts
- LLM 失败率 > 10%（过去 5 分钟）→ Slack #alerts
- SQS 队列深度 > 50 持续 5 分钟 → Slack #alerts
- API p95 响应时间 > 3s         → Slack #alerts
```

---

## 9. 测试策略

### 9.1 测试分层

| 层次 | 范围 | 工具 | 目标覆盖率 |
|---|---|---|---|
| Unit Test | Service 层、Repository 层、Adapter 层、PromptBuilder、重复检测逻辑 | pytest + unittest.mock | 90%+ |
| Integration Test | API 端点（含认证、权限校验）+ 数据库真实写入 | pytest-django + APIClient | 关键路径 100% |
| End-to-End Test | 提交任务 → LLM 处理 → 填写意见 → PDF 生成 全链路 | pytest + Celery EAGER 模式 | 核心 happy path |

---

### 9.2 Unit Test 示例

#### 重复提交检测

```python
# tests/unit/test_diagnosis_service.py
from unittest.mock import patch
from django.test import TestCase
from diagnosis.services import DiagnosisService
from diagnosis.exceptions import DuplicateSubmissionError

class TestDuplicateDetection(TestCase):

    @patch("diagnosis.repositories.DiagnosisRepository.find_recent_by_patient")
    def test_hard_error_within_1h(self, mock_find):
        mock_find.return_value = MockJob(submitted_at=now() - timedelta(minutes=30))
        with self.assertRaises(DuplicateSubmissionError) as ctx:
            DiagnosisService.submit(patient_id=1, structured_data={}, free_text="", user_id=1)
        self.assertEqual(ctx.exception.error_code, "DUPLICATE_SUBMISSION")

    @patch("diagnosis.repositories.DiagnosisRepository.find_recent_by_patient")
    def test_soft_warning_after_1h(self, mock_find):
        mock_find.return_value = MockJob(submitted_at=now() - timedelta(hours=2))
        result = DiagnosisService.submit(patient_id=1, structured_data={}, free_text="", user_id=1)
        self.assertTrue(result.has_warning)
        self.assertEqual(result.warning_type, "POSSIBLE_DUPLICATE")

    @patch("diagnosis.repositories.DiagnosisRepository.find_recent_by_patient")
    def test_no_error_when_no_previous_job(self, mock_find):
        mock_find.return_value = None
        result = DiagnosisService.submit(patient_id=1, structured_data={}, free_text="", user_id=1)
        self.assertFalse(result.has_warning)
```

---

#### LLM Adapter Mock

```python
# tests/unit/test_llm_adapter.py
from unittest.mock import patch, MagicMock
from django.test import override_settings

class TestLLMAdapter(TestCase):

    @patch("adapters.llm.ClaudeAdapter.call")
    def test_claude_called_when_provider_is_claude(self, mock_claude):
        mock_claude.return_value = '{"summary": "test", "differential_diagnosis": [], "recommended_investigations": [], "risk_factors": []}'
        with override_settings(LLM_PROVIDER="claude"):
            result = LLMAdapter.generate("test prompt")
        mock_claude.assert_called_once_with("test prompt")
        self.assertIn("summary", result)

    @patch("adapters.llm.OpenAIAdapter.call")
    def test_openai_called_when_provider_is_openai(self, mock_openai):
        mock_openai.return_value = '{"summary": "test", "differential_diagnosis": [], "recommended_investigations": [], "risk_factors": []}'
        with override_settings(LLM_PROVIDER="openai"):
            LLMAdapter.generate("test prompt")
        mock_openai.assert_called_once()

    @patch("adapters.llm.ClaudeAdapter.call")
    def test_invalid_json_from_llm_raises_error(self, mock_claude):
        mock_claude.return_value = "Not a JSON response"
        with override_settings(LLM_PROVIDER="claude"):
            with self.assertRaises(json.JSONDecodeError):
                LLMAdapter.generate("test prompt")
```

---

#### PDF 生成 Mock

```python
# tests/unit/test_pdf_service.py
@patch("boto3.client")
def test_pdf_uploaded_to_s3(self, mock_boto):
    mock_s3 = MagicMock()
    mock_boto.return_value = mock_s3

    key = PDFService.render_and_upload(
        diagnosis_id="uuid-123",
        job=mock_job,
        report=mock_report,
        opinion=mock_opinion
    )

    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args[1]
    self.assertEqual(call_kwargs["ContentType"], "application/pdf")
    self.assertTrue(key.startswith("reports/uuid-123/"))
```

---

### 9.3 Integration Test 示例

```python
# tests/integration/test_api_diagnosis.py
from rest_framework.test import APIClient

class TestDiagnosisAPI(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.clinician = User.objects.create_user(username="dr_smith", role="clinician")
        self.patient = Patient.objects.create(name="John", date_of_birth="1985-01-01",
                                              gender="male", created_by=self.clinician)
        self.client.force_authenticate(user=self.clinician)

    @patch("diagnosis.tasks.generate_llm_report.delay")  # 不真实入队
    def test_submit_diagnosis_returns_202(self, mock_task):
        response = self.client.post("/api/v1/diagnosis/", {
            "patient_id": self.patient.id,
            "structured_data": {"age": 39, "gender": "male", "temperature": 38.5,
                                 "symptoms": ["cough"], "duration_days": 3,
                                 "existing_conditions": []},
            "free_text": "Patient reports worsening cough."
        }, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertIn("diagnosis_id", response.data)
        mock_task.assert_called_once()

    def test_client_role_cannot_submit_diagnosis(self):
        client_user = User.objects.create_user(username="patient_01", role="client")
        self.client.force_authenticate(user=client_user)
        response = self.client.post("/api/v1/diagnosis/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_client_cannot_access_other_patients_report(self):
        client_user = User.objects.create_user(username="patient_02", role="client")
        self.client.force_authenticate(user=client_user)
        response = self.client.get(f"/api/v1/diagnosis/{self.some_diagnosis_id}/report/")
        self.assertEqual(response.status_code, 403)
```

---

### 9.4 pytest 配置

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests/**/test_*.py
addopts = --cov=. --cov-report=term-missing --cov-fail-under=90
```

```python
# config/settings/test.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_diagnosis_db",
        "HOST": "localhost",
    }
}
CELERY_TASK_ALWAYS_EAGER = True   # Celery 任务同步执行，方便 E2E 测试
LLM_PROVIDER = "mock"             # 测试环境不调用真实 LLM API
```

---

*文档结束。下一步：根据本 Design Doc 生成 Django 项目骨架代码。*
