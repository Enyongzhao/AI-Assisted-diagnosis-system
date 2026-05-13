# Implementation Plan: AI-Assisted Clinical Diagnosis Report System

**基于：** design_doc.md v1.0  
**生成日期：** 2026-05-13  
**状态：** Reviewed & Updated

---

## Plan Review（审核结果）

> 审核维度：Feature 覆盖 / 依赖顺序 / Phase 可运行性 / 简历 Bullet Point 一致性

### ✅ 通过的部分

| # | 检查项 |
|---|---|
| 1 | **所有 12 条简历 bullet point 均有对应实现**：JWT+RBAC、异步 pipeline、PromptBuilder、Adapter 模式、五张核心表、WeasyPrint PDF、SQS+Lambda 迁移、Terraform、Docker Compose、Prometheus+Grafana、90%+ 测试覆盖、分层架构 |
| 2 | **API 端点数量达标**：login/refresh(2) + patients CRUD(4) + diagnosis list/submit/detail/opinion/report(5) + users CRUD(4) = **15 个端点**，超过简历要求的 12+ |
| 3 | **LLM Adapter 完整**：ClaudeAdapter + OpenAIAdapter + MockAdapter，`settings.LLM_PROVIDER` 零代码切换，JSON 解析统一 |
| 4 | **异步双环境覆盖**：本地 Celery+Redis，生产 Lambda+SQS，`tasks/llm_worker.py` + `tasks/pdf_worker.py` 作为 Lambda 入口 |
| 5 | **PDF 链路完整**：WeasyPrint → S3 上传 → Pre-signed URL 15min，与简历描述一致 |
| 6 | **重复检测逻辑完整**：1h 内 Hard Error (400) + 超 1h Soft Warning (202+warning)，三场景均有测试 |
| 7 | **Docker Compose 6 服务齐全**：api + celery_worker + db + redis + prometheus + grafana，与简历 bullet 9 完全一致 |
| 8 | **测试策略完整**：unit/integration/e2e 三层，mock 所有 LLM+S3，`CELERY_TASK_ALWAYS_EAGER=True`，90%+ 覆盖率门槛 |
| 9 | **Controller → Service → Repository 分层贯穿全程**，每层独立可测 |
| 10 | **每个 Phase 均有可验收的终态**（Postman / celery worker / UI / docker / terraform plan / pytest） |

---

### ❌ 需要修改的部分（5 处，已在下方对应章节修复）

---

#### ❌ 问题 1：Repository 层在 Phase 2 才出现，但 Phase 1 的 views 已经需要写库

**问题描述：**  
Phase 1 Step 1.4 的 `PatientViewSet` 需要操作 Patient 数据，Step 1.5 的 `DiagnosisSubmitView` 需要创建 DiagnosisJob 记录。但 `repositories/` 全部文件被放在 Phase 2 Step 2.4 才创建。这意味着 Phase 1 的 views 要么绕过 Repository 直接用 ORM（违反分层架构），要么 Phase 1 结束时根本跑不通。

**修改方案：**  
将 `repositories/patient_repository.py` 和 `repositories/diagnosis_repository.py`（基础 CRUD）移到 **Phase 1 Step 1.2b** 完成，`find_recent_by_patient` 方法和其余 repositories 保留到 Phase 2。Phase 1 的 API views 从第一天起就走 Repository 层，保持分层一致。

→ **已修复**：Phase 1 Step 1.2b 新增 Repository 初始化步骤；Phase 2 Step 2.4 改为"补全剩余 Repository 方法"。

---

#### ❌ 问题 2：`config/exception_handler.py` 只出现在 Phase 4 步骤里，未列入任何模块文件表

**问题描述：**  
Phase 4 Step 4.4 提到"创建 `config/exception_handler.py`，注册 EXCEPTION_HANDLER"，但该文件从未出现在模块三（API 层）的文件列表中。构建时容易漏掉。

**修改方案：**  
将 `config/exception_handler.py` 加入**模块三文件列表**，标注"将自定义异常映射为标准 DRF JSON 错误响应"；Phase 4 Step 4.4 保留引用即可。

→ **已修复**：已加入模块三文件列表。

---

#### ❌ 问题 3：Terraform `modules/api_gateway/main.tf` 文件缺失

**问题描述：**  
`infra/terraform/main.tf` 描述中写明"引用所有子模块（sqs_llm、sqs_pdf、lambda_llm、lambda_pdf、rds、s3、**api_gateway**）"，且简历 Bullet 8 明确提到 "API Gateway"。但模块六文件列表中**没有** `infra/terraform/modules/api_gateway/main.tf`。

**修改方案：**  
在模块六文件列表中增加 `infra/terraform/modules/api_gateway/main.tf`，职责：配置 API Gateway REST API、Lambda proxy integration、JWT Authorizer、rate limiting。

→ **已修复**：已加入模块六文件列表及 Phase 5 Step 5.4。

---

#### ❌ 问题 4：DLQ → SNS 告警的 Lambda 和 Terraform 资源均缺失

**问题描述：**  
Design Doc §6 明确描述 DLQ 处理链路：`SQS DLQ → Lambda（DLQ 处理）→ 写 job_errors + SNS 告警`。当前计划中：
- `tasks/dlq_handler.py` 存在，但没有对应的 Terraform `module "lambda_dlq"` 将其部署为 Lambda 函数
- 没有 `infra/terraform/modules/sns/main.tf`，SNS topic + Slack 订阅无处配置
- Prometheus `dlq_message_count` Gauge 指标也需要 CloudWatch Exporter 才能从 AWS SQS DLQ 拉取数据（见问题 5）

**修改方案：**  
1. 在模块六加入 `infra/terraform/modules/sns/main.tf`（SNS topic + email/Slack 订阅）
2. 在 `infra/terraform/main.tf` 描述中追加 `module "lambda_dlq"`
3. `tasks/dlq_handler.py` 职责描述明确为"**生产环境作为独立 Lambda 函数部署**，由 DLQ SQS event 触发"

→ **已修复**：已加入模块六文件列表及 Phase 5 Step 5.4。

---

#### ❌ 问题 5：`monitoring/prometheus.yml` 引用 `cloudwatch-exporter:9106` 但该服务从未定义

**问题描述：**  
`monitoring/prometheus.yml` 的 scrape config 包含 `targets: ['cloudwatch-exporter:9106']`，用于采集 SQS 队列深度等 AWS CloudWatch 指标。但：
- `docker-compose.yml` 中没有 `cloudwatch-exporter` 服务（本地环境没有 SQS，不需要）
- Terraform 中也没有对应的 ECS task / sidecar 定义
- 不加说明会导致本地 Prometheus 启动时报 scrape 失败告警，误导开发者

**修改方案：**  
将 `monitoring/prometheus.yml` 拆分为两份：
- `monitoring/prometheus.local.yml`：只 scrape `api:8000/metrics`（本地 Celery 队列长度通过 django-prometheus 暴露）
- `monitoring/prometheus.prod.yml`：增加 `cloudwatch-exporter:9106`（生产用）
- `docker-compose.yml` 挂载 `prometheus.local.yml`

→ **已修复**：文件列表拆为两份，docker-compose 注明挂载 local 版本。

---

## 模块拆分总览

```
backend/
├── config/                  # Django 项目配置
├── apps/
│   ├── authentication/      # JWT 认证 + 用户管理
│   ├── patients/            # 患者 CRUD
│   └── diagnosis/           # 诊断核心业务
├── adapters/                # LLM / S3 适配器
├── services/                # 业务逻辑层
├── repositories/            # 数据访问层
├── tasks/                   # Celery 异步任务
└── tests/                   # 测试
frontend/                    # React 前端
infra/                       # Docker + Terraform
monitoring/                  # Prometheus + Grafana 配置
```

---

## 模块一：数据库层

**依赖：** 无（最先实现）

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `apps/authentication/models.py` | 扩展 Django AbstractUser，添加 `role` 字段（admin/clinician/client） |
| `apps/patients/models.py` | Patient 模型，含 `linked_user`、`created_by`、软删除 `is_deleted` |
| `apps/diagnosis/models/diagnosis_job.py` | DiagnosisJob 模型，UUID 主键，结构化字段 + 状态机 + has_warning |
| `apps/diagnosis/models/llm_report.py` | LLMReport 模型，1:1 关联 DiagnosisJob，存结构化输出 + JSONB raw_response |
| `apps/diagnosis/models/doctor_opinion.py` | DoctorOpinion 模型，1:1 关联 DiagnosisJob，Clinician 填写的意见文本 |
| `apps/diagnosis/models/report.py` | Report 模型，存 S3 key + 文件大小，关联 PDF 生成记录 |
| `apps/diagnosis/models/job_error.py` | JobError 模型，记录 DLQ 失败任务，含 retry_count + sqs_message_id |
| `apps/diagnosis/models/__init__.py` | 导出所有 diagnosis 模型 |
| `apps/authentication/migrations/0001_initial.py` | User 表初始 migration |
| `apps/patients/migrations/0001_initial.py` | Patient 表初始 migration |
| `apps/diagnosis/migrations/0001_initial.py` | 五张 diagnosis 表 + 三个索引的初始 migration |

### 模块内依赖顺序
1. `User` model（无外键依赖）
2. `Patient` model（依赖 User）
3. `DiagnosisJob` model（依赖 Patient + User）
4. `LLMReport`、`DoctorOpinion`、`Report`、`JobError`（均依赖 DiagnosisJob）

---

## 模块二：后端 Service 层

**依赖：** 数据库层

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `repositories/diagnosis_repository.py` | DiagnosisJob 的 CRUD + `find_recent_by_patient(patient_id, within_hours)` 用于重复检测 |
| `repositories/llm_report_repository.py` | LLMReport 的创建与查询 |
| `repositories/doctor_opinion_repository.py` | DoctorOpinion 的创建与查询 |
| `repositories/report_repository.py` | Report 记录的创建与查询（S3 key 存储） |
| `repositories/patient_repository.py` | Patient 的 CRUD，支持软删除过滤 |
| `services/diagnosis_service.py` | 提交诊断任务、重复检测逻辑（Hard Error / Soft Warning）、触发异步任务 |
| `services/prompt_builder.py` | 将结构化字段 + 自由文本组合构建 LLM prompt 字符串 |
| `services/pdf_service.py` | 读取 DiagnosisJob + LLMReport + DoctorOpinion，渲染 HTML 模板，WeasyPrint 生成 PDF bytes |
| `services/opinion_service.py` | 保存医生意见、校验当前 status 必须为 `awaiting_doctor_input`、触发 PDF 异步任务 |
| `adapters/llm_adapter.py` | LLMAdapter 统一入口 + ClaudeAdapter + OpenAIAdapter，根据 `settings.LLM_PROVIDER` 路由 |
| `adapters/s3_adapter.py` | 上传 PDF bytes 到 S3，生成 Pre-signed URL（15 分钟有效期） |
| `apps/diagnosis/exceptions.py` | `DuplicateSubmissionError`（硬错误）、`DiagnosisStatusError`（状态机违规）自定义异常 |
| `templates/pdf/report.html` | PDF 报告的 HTML 模板（患者信息 + LLM 分析 + 医生意见） |

### 模块内依赖顺序
1. `repositories/` 全部（依赖 models）
2. `adapters/llm_adapter.py`（无业务依赖）
3. `adapters/s3_adapter.py`（无业务依赖）
4. `services/prompt_builder.py`（无业务依赖）
5. `services/diagnosis_service.py`（依赖 diagnosis_repository）
6. `services/pdf_service.py`（依赖 llm_report_repository + s3_adapter）
7. `services/opinion_service.py`（依赖 diagnosis_repository + opinion_repository）

---

## 模块三：后端 API 层

**依赖：** Service 层、数据库层

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `config/settings/base.py` | Django 基础配置：INSTALLED_APPS、数据库、REST_FRAMEWORK、JWT 设置 |
| `config/settings/local.py` | 本地开发配置，DEBUG=True，读 .env |
| `config/settings/test.py` | 测试配置，CELERY_TASK_ALWAYS_EAGER=True，LLM_PROVIDER="mock" |
| `config/settings/production.py` | 生产配置，从 AWS Secrets Manager 读取密钥 |
| `config/urls.py` | 根 URL 配置，注册 `/api/v1/` 路由 |
| `config/exception_handler.py` | ⬅ 修复问题2：自定义 DRF exception handler，将 DuplicateSubmissionError / DiagnosisStatusError 映射为标准 JSON 错误响应 |
| `apps/authentication/serializers.py` | LoginSerializer（username/password → JWT tokens + user info） |
| `apps/authentication/views.py` | LoginView（POST /auth/login/）、TokenRefreshView（POST /auth/refresh/） |
| `apps/authentication/urls.py` | 认证模块 URL 注册 |
| `apps/authentication/permissions.py` | IsAdmin、IsClinician、IsClient 三个 Permission 类 |
| `apps/patients/serializers.py` | PatientSerializer，含字段校验（gender 枚举、date_of_birth 格式） |
| `apps/patients/views.py` | PatientViewSet（CRUD），DELETE 仅 Admin，软删除实现 |
| `apps/patients/urls.py` | 患者模块 URL 注册 |
| `apps/diagnosis/serializers/diagnosis_serializer.py` | DiagnosisSubmitSerializer（入参）、DiagnosisResponseSerializer（出参，含 llm_report/doctor_opinion） |
| `apps/diagnosis/serializers/opinion_serializer.py` | DoctorOpinionSerializer（text 字段） |
| `apps/diagnosis/views/diagnosis_views.py` | DiagnosisListView、DiagnosisSubmitView（POST，返回 202）、DiagnosisDetailView（GET，轮询） |
| `apps/diagnosis/views/opinion_views.py` | DiagnosisOpinionView（PATCH /diagnosis/{id}/opinion/） |
| `apps/diagnosis/views/report_views.py` | DiagnosisReportView（GET /diagnosis/{id}/report/，生成 Pre-signed URL） |
| `apps/diagnosis/urls.py` | 诊断模块 URL 注册（含嵌套路由） |
| `apps/authentication/admin_views.py` | UserManagementViewSet（Admin only，CRUD 用户 + 角色分配） |

### 模块内依赖顺序
1. `config/settings/` 全部
2. `config/exception_handler.py`
3. `apps/authentication/`（permissions → serializers → views → urls）
4. `apps/patients/`（serializers → views → urls）
5. `apps/diagnosis/serializers/`
6. `apps/diagnosis/views/`（依赖 serializers + services）
7. `config/urls.py`（最后聚合所有 URL）

---

## 模块四：异步任务层

**依赖：** Service 层、数据库层

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `config/celery.py` | 初始化 Celery app，配置 broker（Redis）、backend、任务路由 |
| `config/__init__.py` | 在 Django 启动时加载 Celery app |
| `tasks/llm_task.py` | `generate_llm_report` Celery task，max_retries=3，调用 PromptBuilder + LLMAdapter，失败时更新 status=failed |
| `tasks/pdf_task.py` | `generate_pdf_report` Celery task，max_retries=3，调用 PDFService + S3Adapter，完成后 status=completed |
| `tasks/dlq_handler.py` | ⬅ 修复问题4：DLQ 消息处理逻辑，写入 job_errors 表，发布 SNS 告警；**生产环境打包为独立 Lambda 函数**，由 DLQ SQS event 触发 |
| `tasks/llm_worker.py` | Lambda 入口 handler，从 SQS event 解析 diagnosis_id，调用 generate_llm_report 核心逻辑 |
| `tasks/pdf_worker.py` | Lambda 入口 handler，从 SQS event 解析 diagnosis_id，调用 generate_pdf_report 核心逻辑 |
| `.env.example` | 环境变量模板：DATABASE_URL、REDIS_URL、LLM_PROVIDER、CLAUDE_API_KEY、OPENAI_API_KEY、AWS_* |

### 模块内依赖顺序
1. `config/celery.py`（依赖 settings）
2. `tasks/llm_task.py`（依赖 llm_adapter + repositories）
3. `tasks/pdf_task.py`（依赖 pdf_service + s3_adapter + repositories）
4. `tasks/dlq_handler.py`（依赖 job_error repository）
5. `tasks/llm_worker.py` / `tasks/pdf_worker.py`（依赖对应 task 核心逻辑，Phase 5 时实现）

---

## 模块五：前端

**依赖：** 后端 API 全部就绪

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `frontend/src/api/authApi.ts` | 封装 login、refreshToken 请求，管理 JWT 存储（localStorage） |
| `frontend/src/api/patientApi.ts` | 封装患者 CRUD 请求 |
| `frontend/src/api/diagnosisApi.ts` | 封装提交诊断（POST）、轮询状态（GET）、提交意见（PATCH）、获取 PDF URL（GET）请求 |
| `frontend/src/hooks/usePolling.ts` | 通用轮询 hook，按指数退避策略轮询 diagnosis 状态直到非 pending/processing |
| `frontend/src/pages/LoginPage.tsx` | 登录表单，调用 authApi，保存 token，跳转首页 |
| `frontend/src/pages/DiagnosisListPage.tsx` | 诊断任务列表（分页），根据角色过滤，链接到详情页 |
| `frontend/src/pages/DiagnosisSubmitPage.tsx` | 患者信息表单 + 症状输入，提交后跳转轮询页 |
| `frontend/src/pages/DiagnosisDetailPage.tsx` | 轮询展示 LLM 报告，status=awaiting_doctor_input 时显示意见表单；Clinician 提交意见；status=completed 时显示 PDF 下载按钮 |
| `frontend/src/pages/ReportDownloadPage.tsx` | 调用 /report/ 获取 Pre-signed URL，自动跳转下载（Client 角色入口） |
| `frontend/src/components/StatusBadge.tsx` | 根据 diagnosis status 显示彩色标签（pending/processing/awaiting_doctor_input/completed/failed） |
| `frontend/src/components/WarningBanner.tsx` | 显示 POSSIBLE_DUPLICATE 软警告横幅 |
| `frontend/src/context/AuthContext.tsx` | 全局认证状态管理，提供 user、role、logout |
| `frontend/src/router/PrivateRoute.tsx` | 基于角色的路由守卫，未认证跳转 /login |

### 模块内依赖顺序
1. `api/` 层（authApi → patientApi → diagnosisApi）
2. `context/AuthContext.tsx`
3. `hooks/usePolling.ts`
4. `components/`（无页面依赖）
5. `pages/`（LoginPage → DiagnosisSubmitPage → DiagnosisDetailPage → DiagnosisListPage → ReportDownloadPage）
6. `router/PrivateRoute.tsx`（依赖 AuthContext）

---

## 模块六：基础设施

**依赖：** 所有业务代码就绪

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `Dockerfile` | 多阶段构建：基于 python:3.11-slim，安装 WeasyPrint 系统依赖（pango/cairo），暴露 8000 |
| `docker-compose.yml` | 编排 api + celery_worker + db(postgres:15) + redis(redis:7-alpine) + prometheus + grafana；prometheus 挂载 prometheus.local.yml |
| `.dockerignore` | 排除 .env、__pycache__、.git、node_modules 等不需要打包的文件 |
| `infra/terraform/main.tf` | Terraform 根模块，引用 sqs_llm、sqs_pdf、lambda_llm、lambda_pdf、**lambda_dlq**、rds、s3、**api_gateway**、**sns** 共九个子模块 |
| `infra/terraform/variables.tf` | 所有 Terraform 输入变量声明（环境名、实例类型、AWS region 等） |
| `infra/terraform/outputs.tf` | 输出关键资源 ARN/URL（API Gateway URL、RDS endpoint、S3 bucket name） |
| `infra/terraform/modules/sqs/main.tf` | SQS 队列 + DLQ 子模块（visibility_timeout、max_receive_count 可配置） |
| `infra/terraform/modules/lambda/main.tf` | Lambda 函数子模块，配置 SQS 事件源、timeout、env vars、IAM role |
| `infra/terraform/modules/rds/main.tf` | RDS PostgreSQL 子模块，multi-AZ、自动备份、Secrets Manager 集成 |
| `infra/terraform/modules/s3/main.tf` | S3 bucket 子模块，配置 bucket policy、版本控制、CORS（Pre-signed URL 支持） |
| `infra/terraform/modules/api_gateway/main.tf` | ⬅ 修复问题3：API Gateway REST API，配置 Lambda proxy integration、JWT Authorizer、rate limiting |
| `infra/terraform/modules/sns/main.tf` | ⬅ 修复问题4：SNS topic 子模块，配置 DLQ 告警订阅（email / Slack webhook via Lambda） |
| `monitoring/prometheus.local.yml` | ⬅ 修复问题5：本地 scrape 配置，只采集 `api:8000/metrics`（无 CloudWatch exporter） |
| `monitoring/prometheus.prod.yml` | ⬅ 修复问题5：生产 scrape 配置，增加 `cloudwatch-exporter:9106`（采集 SQS 队列深度） |
| `monitoring/grafana/dashboards/system_health.json` | Grafana System Health 仪表盘 JSON（任务提交量、完成率、SQS 队列深度、DLQ 告警） |
| `monitoring/grafana/dashboards/llm_performance.json` | Grafana LLM Performance 仪表盘 JSON（耗时 p50/p95/p99、token 趋势、失败率） |
| `monitoring/grafana/dashboards/api_traffic.json` | Grafana API Traffic 仪表盘 JSON（endpoint 请求量、4xx/5xx 错误率、响应时间 p95） |
| `monitoring/grafana/alert_rules.yml` | 四条告警规则（DLQ>0、LLM失败率>10%、SQS深度>50、API p95>3s → Slack） |

---

## 模块七：测试

**依赖：** 所有业务代码（随业务代码同步开发）

### 需要创建的文件

| 文件 | 职责 |
|---|---|
| `pytest.ini` | pytest 配置：DJANGO_SETTINGS_MODULE=test，覆盖率要求 90%+ |
| `tests/conftest.py` | 全局 fixtures：clinician_user、admin_user、client_user、sample_patient、authenticated_api_client |
| `tests/unit/test_diagnosis_service.py` | 重复检测三个场景（1h 内 Hard Error、超 1h Soft Warning、无历史记录） |
| `tests/unit/test_llm_adapter.py` | LLM Adapter 路由测试（claude/openai 切换）、JSON 解析失败异常 |
| `tests/unit/test_prompt_builder.py` | PromptBuilder 输出包含所有结构化字段和自由文本 |
| `tests/unit/test_pdf_service.py` | PDFService 生成 PDF bytes 非空、S3 上传被调用、Content-Type 正确（mock boto3） |
| `tests/unit/test_opinion_service.py` | 状态校验（非 awaiting_doctor_input 状态提交意见应抛异常）、触发 PDF 任务 |
| `tests/integration/test_api_auth.py` | 登录成功返回 JWT、错误密码返回 401、token 刷新正常 |
| `tests/integration/test_api_patients.py` | Clinician 创建患者 201、Client 无权创建 403、Admin 软删除患者 |
| `tests/integration/test_api_diagnosis.py` | 提交诊断返回 202、Client 无权提交 403、跨患者报告访问 403、轮询状态转换 |
| `tests/integration/test_api_opinion.py` | Clinician 提交意见 200、非提交者提交意见 403、状态错误时提交意见 400 |
| `tests/integration/test_api_report.py` | Clinician 获取自己的 PDF URL 200、Client 只能访问本人 200、跨用户 403 |
| `tests/e2e/test_full_pipeline.py` | 全链路 E2E：提交 → Celery EAGER 执行 LLM task → 轮询到 awaiting_doctor_input → 提交意见 → PDF 生成 → status=completed |
| `tests/mocks/llm_mock.py` | MockLLMAdapter，返回固定 JSON 结构，用于 E2E 测试不调用真实 API |

---

## 实现顺序

### Phase 1：数据库 + 后端 API（能 CRUD）

**目标：** 所有 API 端点可以调用，数据库读写正常，JWT 认证和 RBAC 生效

```
Step 1.1  项目初始化
  - django-admin startproject config .
  - pip install djangorestframework djangorestframework-simplejwt psycopg2-binary

Step 1.2  数据库层（模块一）
  - 创建 User、Patient、DiagnosisJob、LLMReport、DoctorOpinion、Report、JobError models
  - 运行 makemigrations + migrate

Step 1.2b  Repository 基础层（修复问题1）
  - repositories/patient_repository.py（CRUD，供 PatientViewSet 使用）
  - repositories/diagnosis_repository.py（基础 CRUD，暂不含 find_recent_by_patient）
  - 确保所有 views 从第一天起就通过 Repository 访问数据，保持分层一致

Step 1.3  认证 API
  - apps/authentication/permissions.py  →  serializers.py  →  views.py  →  urls.py
  - POST /api/v1/auth/login/  +  POST /api/v1/auth/refresh/

Step 1.4  患者 CRUD API
  - apps/patients/serializers.py  →  views.py（调用 patient_repository）  →  urls.py
  - GET/POST/PUT/DELETE /api/v1/patients/

Step 1.5  诊断任务基础 API（先不接异步）
  - diagnosis/serializers/  →  views/diagnosis_views.py（调用 diagnosis_repository，status=pending 同步返回）
  - GET/POST /api/v1/diagnosis/  +  GET /api/v1/diagnosis/{id}/

Step 1.6  Admin 用户管理 API
  - authentication/admin_views.py
  - GET/POST/PUT/DELETE /api/v1/users/

Step 1.7  Exception Handler 注册（修复问题2）
  - config/exception_handler.py
  - config/settings/base.py 中注册 EXCEPTION_HANDLER
```

**验收标准：** `docker compose up` 后，用 Postman/curl 能完整走通认证 + 患者 CRUD + 提交诊断任务（同步返回 pending）；所有 views 走 Repository 层，无直接 ORM 调用

---

### Phase 2：异步任务（Celery + Redis）

**目标：** 提交诊断后 LLM 异步调用，轮询接口能看到 processing → awaiting_doctor_input 状态变化

```
Step 2.1  Celery 基础配置
  - config/celery.py  +  config/__init__.py
  - pip install celery redis

Step 2.2  LLM Adapter
  - adapters/llm_adapter.py（ClaudeAdapter + OpenAIAdapter + MockAdapter）
  - pip install anthropic openai

Step 2.3  PromptBuilder
  - services/prompt_builder.py

Step 2.4  补全 Repository 层（修复问题1）
  - repositories/diagnosis_repository.py 补充 find_recent_by_patient（Phase 4 重复检测用）
  - repositories/llm_report_repository.py
  - repositories/doctor_opinion_repository.py
  - repositories/report_repository.py

Step 2.5  LLM Celery Task
  - tasks/llm_task.py（generate_llm_report，max_retries=3）
  - DiagnosisSubmitView 改为调用 generate_llm_report.delay()

Step 2.6  S3 Adapter + PDFService
  - adapters/s3_adapter.py（upload + generate_presigned_url）
  - services/pdf_service.py + templates/pdf/report.html
  - pip install weasyprint boto3

Step 2.7  PDF Celery Task
  - tasks/pdf_task.py（generate_pdf_report，max_retries=3）
  - services/opinion_service.py 提交意见后调用 generate_pdf_report.delay()

Step 2.8  意见 + 报告 API
  - views/opinion_views.py（PATCH /diagnosis/{id}/opinion/）
  - views/report_views.py（GET /diagnosis/{id}/report/）
```

**验收标准：** `celery -A config worker` 启动后，提交诊断 → 30 秒内轮询到 awaiting_doctor_input → 提交意见 → 轮询到 completed → GET /report/ 返回 Pre-signed URL

---

### Phase 3：前端（表单 + 轮询）

**目标：** 完整的 Web UI，三个角色均可使用

```
Step 3.1  项目初始化
  - npx create-react-app frontend --template typescript
  - npm install axios react-router-dom

Step 3.2  API 层
  - api/authApi.ts  →  api/patientApi.ts  →  api/diagnosisApi.ts

Step 3.3  认证 + 路由
  - context/AuthContext.tsx
  - router/PrivateRoute.tsx
  - pages/LoginPage.tsx

Step 3.4  诊断提交
  - pages/DiagnosisSubmitPage.tsx（结构化字段表单 + free_text textarea）

Step 3.5  轮询 + 结果展示
  - hooks/usePolling.ts（3 秒一次，状态到终态后停止）
  - pages/DiagnosisDetailPage.tsx（展示 llm_report + 意见表单 + PDF 下载按钮）
  - components/StatusBadge.tsx  +  components/WarningBanner.tsx

Step 3.6  列表 + 下载
  - pages/DiagnosisListPage.tsx（分页列表，基于角色过滤）
  - pages/ReportDownloadPage.tsx（Client 下载入口）
```

**验收标准：** 三个角色 (admin/clinician/client) 均能完整走通自己的操作路径；轮询在 status=completed 后自动停止；PDF 可下载

---

### Phase 4：业务验证（重复检测、Error/Warning）

**目标：** 重复提交防护逻辑完整可用，自定义异常正确映射到 HTTP 状态码

```
Step 4.1  重复检测核心逻辑
  - repositories/diagnosis_repository.py 中 find_recent_by_patient（已在 Phase 2 Step 2.4 创建）
  - diagnosis/exceptions.py（DuplicateSubmissionError + DiagnosisStatusError）

Step 4.2  DiagnosisService 集成验证
  - services/diagnosis_service.py：
      - 1h 内 → raise DuplicateSubmissionError → exception_handler 返回 400
      - 超 1h 存在 → 设置 has_warning=True, warning_type="POSSIBLE_DUPLICATE" → 正常 202 + warning 字段
      - 无历史 → 正常 202

Step 4.3  意见提交状态校验
  - services/opinion_service.py：检查 status == awaiting_doctor_input，否则 raise DiagnosisStatusError

Step 4.4  Exception Handler 完善
  - config/exception_handler.py（已在 Phase 1 Step 1.7 创建框架，此处补充两个自定义异常映射）
  - 确认 config/settings/base.py 中已注册

Step 4.5  前端处理 Warning Banner
  - DiagnosisDetailPage.tsx 中检查 response.warning == "POSSIBLE_DUPLICATE"，渲染 WarningBanner
```

**验收标准：** 对同一患者在 1h 内二次提交 → 返回 400 + DUPLICATE_SUBMISSION；在 1h 后提交 → 返回 202 + warning 字段；前端正确展示警告横幅

---

### Phase 5：Docker + 部署

**目标：** `docker compose up --build` 一键启动本地全套环境；Terraform 能 plan/apply AWS 资源

```
Step 5.1  Dockerfile
  - 多阶段构建，安装系统依赖（WeasyPrint 需要 pango/cairo/libffi）
  - 最终镜像基于 python:3.11-slim

Step 5.2  docker-compose.yml
  - 6 个服务：api + celery_worker + db + redis + prometheus + grafana
  - prometheus 挂载 monitoring/prometheus.local.yml（不含 cloudwatch-exporter）
  - 健康检查：db、redis 就绪后再启动 api/celery
  - volumes：pg_data 持久化

Step 5.3  .env 管理
  - .env.example 列出所有必填变量
  - docker-compose 通过 env_file 注入

Step 5.4  Terraform 模块（修复问题3、4）
  - infra/terraform/modules/sqs/main.tf
  - infra/terraform/modules/lambda/main.tf（含 IAM role + SQS event source）
  - infra/terraform/modules/rds/main.tf
  - infra/terraform/modules/s3/main.tf
  - infra/terraform/modules/api_gateway/main.tf（REST API + JWT Authorizer + rate limit）
  - infra/terraform/modules/sns/main.tf（DLQ 告警 topic + 订阅）
  - infra/terraform/main.tf（module "lambda_dlq" 使用 lambda 模块，trigger = DLQ SQS）
  - infra/terraform/variables.tf + outputs.tf

Step 5.5  Lambda 入口适配
  - tasks/llm_worker.py（Lambda handler，从 SQS event 解析 diagnosis_id）
  - tasks/pdf_worker.py（同上）
  - tasks/dlq_handler.py 确认可作为 Lambda handler 部署（handler 函数签名 event/context）

Step 5.6  Prometheus 配置拆分（修复问题5）
  - monitoring/prometheus.local.yml（本地用，只 scrape api:8000/metrics）
  - monitoring/prometheus.prod.yml（生产用，增加 cloudwatch-exporter:9106）
```

**验收标准：** `docker compose up --build` 启动后所有服务 healthy；`terraform plan` 输出无错误（dry-run，不需要真实 AWS 账号）；prometheus 本地启动无 scrape 失败告警

---

### Phase 6：监控 + 测试

**目标：** 90%+ 单元测试覆盖率；Grafana 三个 Dashboard 正常显示；告警规则配置完成

```
Step 6.1  pytest 配置
  - pytest.ini + config/settings/test.py（CELERY_TASK_ALWAYS_EAGER=True）
  - tests/conftest.py（全局 fixtures）
  - tests/mocks/llm_mock.py（MockLLMAdapter）

Step 6.2  单元测试
  - tests/unit/test_diagnosis_service.py（重复检测三场景）
  - tests/unit/test_llm_adapter.py（provider 路由 + JSON 解析异常）
  - tests/unit/test_prompt_builder.py
  - tests/unit/test_pdf_service.py（mock boto3）
  - tests/unit/test_opinion_service.py

Step 6.3  集成测试
  - tests/integration/test_api_auth.py
  - tests/integration/test_api_patients.py
  - tests/integration/test_api_diagnosis.py
  - tests/integration/test_api_opinion.py
  - tests/integration/test_api_report.py

Step 6.4  E2E 测试
  - tests/e2e/test_full_pipeline.py（全链路，Celery EAGER 模式）

Step 6.5  Prometheus 指标集成
  - pip install django-prometheus
  - 在 INSTALLED_APPS 和 urls.py 注册 /metrics 端点
  - 在 llm_task 和 pdf_task 中记录自定义 Histogram/Counter 指标
    （llm_report_duration_seconds、pdf_generation_duration_seconds、llm_api_tokens_total）

Step 6.6  Grafana Dashboard
  - monitoring/grafana/dashboards/ 三个 JSON 文件
  - monitoring/grafana/alert_rules.yml（Slack webhook 告警）

Step 6.7  运行覆盖率检查
  - pytest --cov=. --cov-report=term-missing --cov-fail-under=90
```

**验收标准：** `pytest` 覆盖率 ≥ 90%；`docker compose up` 后访问 localhost:3000 能看到 Grafana 三个 Dashboard；提交一次诊断任务后，System Health 面板任务提交量 +1

---

## 模块依赖关系图

```
数据库层（models + migrations）
    │
    ├──► Repository 层（Phase 1 基础 CRUD，Phase 2 补全）
    │        │
    │        ├──► Service 层（diagnosis_service, opinion_service, pdf_service）
    │        │        │
    │        │        └──► Async Tasks（llm_task, pdf_task）
    │        │                   │
    │        │        ┌──────────┘
    │        │        │
    │        └──► API 层（views, serializers, urls, exception_handler）
    │                   │
    │                   └──► 前端（api/, pages/, hooks/）
    │
    ├──► LLM Adapter（独立，被 llm_task 调用）
    ├──► S3 Adapter（独立，被 pdf_task 调用）
    └──► PromptBuilder（独立，被 llm_task 调用）

基础设施（Docker, Terraform: SQS×2 + DLQ×2 + Lambda×3 + RDS + S3 + API Gateway + SNS）
    └── 依赖所有业务代码

监控（prometheus.local / prometheus.prod + Grafana）
    └── 依赖 API 层 + 基础设施

测试（pytest）── 依赖所有业务代码（并行开发，Phase 6 补齐覆盖率）
```

---

## 关键技术决策备注

| 决策点 | 方案 | 原因 |
|---|---|---|
| 异步任务双环境 | 本地 Celery + Redis，生产 Lambda + SQS | 本地调试方便，生产弹性伸缩 |
| LLM Adapter 模式 | 统一 `generate(prompt) → dict` 接口 | 业务层零感知切换 Claude/OpenAI |
| 重复检测时间窗口 | 1h 内 Hard Error，超 1h Soft Warning | 见 design_doc §4.3 |
| PDF 存储 | S3 + Pre-signed URL（15min 有效期） | 不暴露真实 S3 地址，安全可控 |
| 测试 LLM 隔离 | `LLM_PROVIDER=mock` + MockLLMAdapter | 不产生真实 API 费用，测试稳定 |
| UUID 主键 | DiagnosisJob 使用 UUID | 避免 ID 枚举攻击，与 API 设计一致 |
| Repository 创建时机 | Phase 1 就建基础 CRUD | 分层架构从第一行代码就一致，避免后期重构 |
| Prometheus 配置拆分 | local.yml / prod.yml 分离 | 本地无 CloudWatch exporter，分开避免 scrape 错误 |
| DLQ Lambda 独立部署 | lambda_dlq 独立 Terraform 模块 | DLQ 处理逻辑与业务 Lambda 解耦，单独扩缩容 |

---

*计划结束。按 Phase 1 → Phase 6 顺序实现，每个 Phase 结束后验收再进入下一阶段。*
