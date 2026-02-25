# Bilibili Comment Assistant - AI 中控台架构规划

## 一、总体架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Web Frontend (Vue/React)                      │
│  用户输入需求 → 确认验收标准 → 实时监控 → 接收交付报告                      │
├─────────────────────────────────────────────────────────────────────┤
│                    FastAPI Web Backend (异步)                         │
│  WebSocket实时通信 │ REST API │ SSE事件推送                             │
├──────────┬──────────────────────────────────────────────────────────┤
│          │            AI Control Center (中控台核心)                   │
│          │  ┌─────────────────────────────────────────────────┐     │
│          │  │  Planner       - 需求拆解 & 验收标准生成          │     │
│          │  │  Dispatcher    - 任务调度 & 模型路由              │     │
│          │  │  Executor      - 多轮执行循环                    │     │
│          │  │  Validator     - 验收确认 & 交叉验证              │     │
│          │  │  Reporter      - 结果汇总 & 交付                 │     │
│          │  └─────────────────────────────────────────────────┘     │
├──────────┴──────────────────────────────────────────────────────────┤
│                     Module Registry (功能模块注册中心)                 │
│  统一接口标准 │ 模块自注册 │ 能力描述 │ 参数Schema                      │
├─────────────────────────────────────────────────────────────────────┤
│                   Functional Modules (功能模块层)                     │
│  AuthModule │ SearchModule │ CommentModule │ WarmupModule │          │
│  AIGenModule │ FilterModule │ HistoryModule │ CaptchaModule │ ...   │
├─────────────────────────────────────────────────────────────────────┤
│                  Browser Pool (浏览器池)                              │
│  BrowserManager: 多Playwright实例管理、分配、回收                       │
├─────────────────────────────────────────────────────────────────────┤
│                  Multi-Model AI Provider Layer                       │
│  ModelRouter │ ProviderA(DeepSeek) │ ProviderB(GPT) │ ProviderC │   │
└─────────────────────────────────────────────────────────────────────┘
```

## 二、功能模块拆分（Module Registry）

### 2.1 模块接口标准

每个功能模块必须实现统一的 `IModule` 接口：

```python
# modules/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from enum import Enum

class ModuleCapability(BaseModel):
    """模块能力描述 - 供AI读取理解"""
    name: str                          # 模块名称
    description: str                   # 自然语言描述（AI可读）
    actions: List["ActionSpec"]        # 可执行的操作列表
    requires_browser: bool             # 是否需要浏览器实例
    requires_auth: bool                # 是否需要登录态
    category: str                      # 分类: "browser_automation", "data_processing", "ai_generation", "system"

class ActionSpec(BaseModel):
    """单个操作的规格描述"""
    name: str                          # 操作名称 (如 "search_videos")
    description: str                   # 自然语言描述
    parameters: Dict[str, "ParamSpec"] # 参数定义
    returns: Dict[str, str]            # 返回值描述
    side_effects: List[str]            # 副作用描述 (如 "posts a comment", "modifies history")
    estimated_duration: str            # 预估耗时 ("fast"/<1s, "medium"/1-10s, "slow"/>10s)
    risk_level: str                    # 风险等级 ("safe", "moderate", "high")

class ParamSpec(BaseModel):
    """参数规格"""
    type: str                          # "string", "int", "float", "bool", "list", "dict"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None   # 可选枚举值
    constraints: Optional[Dict] = None # 约束 (min, max, pattern等)

class ActionResult(BaseModel):
    """操作执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = {}       # 执行指标(耗时, 重试次数等)
    logs: List[str] = []               # 执行日志

class IModule(ABC):
    """所有功能模块的基础接口"""
    
    @abstractmethod
    def get_capability(self) -> ModuleCapability:
        """返回模块能力描述（AI可读）"""
        pass
    
    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any], context: "ExecutionContext") -> ActionResult:
        """执行指定操作"""
        pass
    
    @abstractmethod
    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        """验证参数合法性"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """模块健康检查"""
        pass
```

### 2.2 从现有代码拆分的功能模块清单

| 模块ID | 模块名称 | 原始来源 | 类别 | 需要浏览器 | 需要登录 |
|--------|----------|----------|------|------------|----------|
| auth | 认证模块 | core/auth.py | system | Yes | No |
| search | 视频搜索模块 | core/search.py | browser_automation | Yes | No |
| comment | 评论发布模块 | core/comment.py | browser_automation | Yes | Yes |
| warmup | 账号养号模块 | core/warmup.py | browser_automation | Yes | Yes |
| ai_gen | AI内容生成模块 | core/ai_manager.py + core/ai_provider.py | ai_generation | No | No |
| ai_filter | AI视频筛选模块 | core/ai_manager.py | ai_generation | No | No |
| history | 历史记录模块 | core/history.py | data_processing | No | No |
| captcha | 验证码管理模块 | core/captcha_tracker.py + core/captcha_check.py | system | Partial | No |
| config | 配置管理模块 | core/config.py | system | No | No |
| notify | 通知模块 | core/notifier.py | system | No | No |
| browser_pool | 浏览器池模块 | 新建（基于main.py的launch逻辑） | system | N/A | No |
| report | 报告模块 | 新建（基于main.py的CSV日志） | data_processing | No | No |

### 2.3 每个模块的详细Action定义

#### auth 模块

- `login_with_cookies(cookie_file: str)` → `{logged_in: bool}`
- `login_with_qrcode()` → `{logged_in: bool, qr_image_path: str}`
- `check_login_status()` → `{logged_in: bool, username: str}`
- `save_cookies(path: str)` → `{saved: bool}`

#### search 模块

- `search_videos(keyword, max_count, order, duration, time_range)` → `{videos: [{url, bv, title, author, date, views, comments}]}`
- `get_current_page_videos(max_count)` → `{videos: [...]}`
- `go_to_next_page()` → `{success: bool, has_next: bool}`

#### comment 模块

- `post_comment(url, text, image_path?)` → `{status: "success"|"captcha"|"failed"}`
- `check_captcha()` → `{has_captcha: bool}`

#### warmup 模块

- `run_warmup(duration_minutes, max_videos, behavior_config)` → `{stats: {watched, time, likes}}`
- `watch_single_video(url, watch_time, behavior_config)` → `{watched: bool, duration: int}`
- `like_video(url)` → `{liked: bool}`

#### ai_gen 模块

- `generate_comment(video_info, persona, style, max_length)` → `{comment: str}`
- `generate_batch_comments(video_list, persona, style)` → `{comments: [{bv, comment}]}`

#### ai_filter 模块

- `check_relevance(video_info, criteria)` → `{keep: bool, reason: str}`
- `batch_filter(video_list, criteria)` → `{results: [{bv, keep, reason}]}`

#### history 模块

- `check_visited(video_id)` → `{visited: bool}`
- `mark_visited(video_id)` → `{added: bool}`
- `get_all_visited()` → `{video_ids: [str], count: int}`
- `clear_history()` → `{cleared: bool}`

#### captcha 模块

- `check_page_captcha(page_id)` → `{has_captcha: bool}`
- `record_captcha_event()` → `{today_count: int}`
- `get_cooldown(base_minutes)` → `{cooldown_minutes: int}`
- `get_today_stats()` → `{count: int, date: str}`

#### config 模块

- `load_config(path?)` → `{config: dict}`
- `save_config(config, path?)` → `{saved: bool}`
- `validate_config(config)` → `{valid: bool, errors: [str]}`
- `get_default_config()` → `{config: dict}`

#### browser_pool 模块（新建）

- `acquire_browser(headed?, custom_path?)` → `{browser_id: str, pages: [page_id]}`
- `release_browser(browser_id)` → `{released: bool}`
- `create_page(browser_id)` → `{page_id: str}`
- `close_page(page_id)` → `{closed: bool}`
- `get_pool_status()` → `{total, active, idle, browsers: [{id, pages, status}]}`

#### report 模块（新建）

- `log_result(video_info, status, comment, source)` → `{logged: bool}`
- `get_session_report(session_id)` → `{summary: {total, success, failed, captcha}, details: [...]}`
- `export_csv(session_id, path)` → `{exported: bool, path: str}`

## 三、AI 中控台核心架构

### 3.1 核心组件

```
┌──────────────────────────────────────────────────────────┐
│                   AI Control Center                       │
│                                                          │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────┐   │
│  │ Planner  │──>│ Dispatcher │──>│    Executor      │   │
│  │ (规划器)  │   │ (调度器)    │   │   (执行引擎)     │   │
│  └──────────┘   └────────────┘   └────────┬─────────┘   │
│       ▲                                    │             │
│       │              ┌─────────────────────┘             │
│       │              ▼                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐     │
│  │ Reporter │<──│ Validator│<──│  Task State      │     │
│  │ (报告器)  │   │ (验收器)  │   │  Machine (FSM)   │     │
│  └──────────┘   └──────────┘   └──────────────────┘     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │            Model Router (模型路由器)               │    │
│  │  Task Type → Model Mapping + Load Balancing       │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Planner（规划器）—— 需求拆解与验收标准

Planner 是用户需求进入系统后的第一个 AI 处理环节。

**职责：**

- 解析用户自然语言需求
- 查询 Module Registry 获取可用模块和能力
- 判断需求的可行性
- 将需求拆解为具体的 Task DAG（有向无环图）
- 为每个子任务生成验收标准
- 估算整体执行时间和风险

**核心流程：**

```python
class Planner:
    async def plan(self, user_request: str) -> ExecutionPlan:
        # 1. 读取所有已注册模块的 capability 描述
        capabilities = self.module_registry.get_all_capabilities()
        
        # 2. 调用规划模型，拆解需求
        plan_prompt = self._build_plan_prompt(user_request, capabilities)
        raw_plan = await self.model_router.call(
            task_type="planning",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=plan_prompt
        )
        
        # 3. 解析为结构化的执行计划
        execution_plan = self._parse_plan(raw_plan)
        
        # 4. 验证计划的可行性（检查模块是否存在、参数是否合法）
        feasibility = await self._validate_feasibility(execution_plan)
        
        # 5. 生成验收标准
        acceptance_criteria = await self._generate_acceptance_criteria(
            user_request, execution_plan
        )
        
        return ExecutionPlan(
            tasks=execution_plan.tasks,
            dag=execution_plan.dependency_graph,
            acceptance_criteria=acceptance_criteria,
            estimated_duration=execution_plan.estimate,
            risk_assessment=feasibility.risks
        )
```

**ExecutionPlan 数据结构：**

```python
class TaskNode(BaseModel):
    task_id: str
    description: str                    # 自然语言描述
    module_id: str                      # 调用哪个模块
    action: str                         # 调用哪个操作
    params: Dict[str, Any]             # 参数（可引用前置任务的输出）
    depends_on: List[str]              # 依赖的前置task_id
    acceptance: AcceptanceCriteria     # 子任务验收标准
    assigned_model: Optional[str]      # 指定AI模型（None=自动路由）
    retry_policy: RetryPolicy          # 重试策略
    risk_level: str                    # "safe" / "moderate" / "high"

class AcceptanceCriteria(BaseModel):
    description: str                   # 自然语言描述
    checkpoints: List[Checkpoint]      # 具体检查点

class Checkpoint(BaseModel):
    check_type: str                    # "value_match", "count_gte", "status_equals", "custom_ai_judge"
    field: str                         # 检查哪个输出字段
    expected: Any                      # 期望值
    tolerance: Optional[float]         # 容差

class ExecutionPlan(BaseModel):
    plan_id: str
    original_request: str
    tasks: List[TaskNode]
    dag: Dict[str, List[str]]         # task_id -> [dependent_task_ids]
    acceptance_criteria: AcceptanceCriteria  # 整体验收标准
    estimated_duration: int            # 预估秒数
    risk_assessment: str
```

### 3.3 Model Router（模型路由器）

根据任务类型分配不同的 AI 模型：

```python
class ModelRouter:
    """
    任务类型 -> 模型映射 + 故障转移
    """
    def __init__(self, config: ModelRouterConfig):
        self.providers: Dict[str, AIProvider] = {}  # model_id -> provider
        self.routing_table: Dict[str, ModelRoute] = {}
        # 示例路由表:
        # "planning"       -> deepseek-chat (擅长中文理解和逻辑推理)
        # "comment_gen"    -> deepseek-chat / qwen
        # "video_filter"   -> deepseek-chat (快速判断)
        # "validation"     -> gpt-4o (严格验证，用不同模型交叉验证)
        # "summarize"      -> deepseek-chat
    
    async def call(self, task_type: str, system_prompt: str, 
                   user_prompt: str, fallback: bool = True) -> str:
        route = self.routing_table[task_type]
        primary = self.providers[route.primary_model]
        try:
            return await primary.chat(system_prompt, user_prompt)
        except Exception as e:
            if fallback and route.fallback_model:
                return await self.providers[route.fallback_model].chat(
                    system_prompt, user_prompt
                )
            raise

    async def cross_validate(self, task_type: str, prompt: str, 
                             models: List[str], strategy: str = "majority") -> CrossValidationResult:
        """
        交叉验证：同一个prompt发给多个模型，比较结果
        strategy: "majority" (多数投票), "consensus" (全部一致), "best_of" (取最优)
        """
        results = await asyncio.gather(*[
            self.providers[m].chat(VALIDATOR_SYSTEM, prompt) 
            for m in models
        ])
        return self._resolve(results, strategy)
```

**路由配置：**

```python
class ModelRoute(BaseModel):
    primary_model: str           # 主模型
    fallback_model: Optional[str] # 备用模型
    timeout: int = 30
    max_retries: int = 2

class ModelRouterConfig(BaseModel):
    providers: Dict[str, ProviderConfig]  # 模型提供商配置
    routes: Dict[str, ModelRoute]         # 任务类型路由
    cross_validation: CrossValidationConfig

# 示例配置
default_router_config = {
    "providers": {
        "deepseek": {"base_url": "https://api.deepseek.com/v1", "api_key": "...", "model": "deepseek-chat"},
        "openai": {"base_url": "https://api.openai.com/v1", "api_key": "...", "model": "gpt-4o-mini"},
        "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key": "...", "model": "qwen-plus"},
    },
    "routes": {
        "planning": {"primary_model": "deepseek", "fallback_model": "openai"},
        "comment_gen": {"primary_model": "deepseek", "fallback_model": "qwen"},
        "video_filter": {"primary_model": "deepseek", "fallback_model": "qwen"},
        "validation": {"primary_model": "openai", "fallback_model": "deepseek"},
        "summarize": {"primary_model": "deepseek"},
    }
}
```

### 3.4 Dispatcher（调度器）—— 任务调度与浏览器资源管理

```python
class Dispatcher:
    """
    根据DAG依赖关系调度任务，管理浏览器资源
    """
    def __init__(self, browser_pool: BrowserPool, module_registry: ModuleRegistry):
        self.browser_pool = browser_pool
        self.module_registry = module_registry
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    
    async def dispatch(self, plan: ExecutionPlan) -> AsyncGenerator[TaskEvent, None]:
        """
        按DAG拓扑序调度任务，无依赖的任务并行执行
        """
        # 拓扑排序，找出可并行执行的任务层
        layers = self._topological_layers(plan.dag)
        
        for layer in layers:
            # 同一层的任务可以并行
            tasks = [plan.get_task(tid) for tid in layer]
            
            # 为需要浏览器的任务分配浏览器实例
            for task in tasks:
                module = self.module_registry.get(task.module_id)
                if module.get_capability().requires_browser:
                    browser = await self.browser_pool.acquire()
                    task.context.browser = browser
            
            # 并行执行本层所有任务
            results = await asyncio.gather(*[
                self._execute_task(task) for task in tasks
            ], return_exceptions=True)
            
            # 将结果传递给下游依赖任务
            for task, result in zip(tasks, results):
                yield TaskEvent(task_id=task.task_id, result=result)
```

### 3.5 Executor（执行引擎）—— 多轮循环执行

这是核心的执行循环，负责实际调用模块并处理结果：

```python
class Executor:
    """
    执行引擎 - 多轮循环执行直到验收通过
    """
    MAX_ROUNDS = 10  # 最大执行轮次，防止无限循环
    
    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionReport:
        session = ExecutionSession(plan)
        
        for round_num in range(1, self.MAX_ROUNDS + 1):
            session.current_round = round_num
            await self.event_bus.emit("round_start", {"round": round_num})
            
            # 1. 调度并执行当前轮次的任务
            async for event in self.dispatcher.dispatch(plan):
                task = plan.get_task(event.task_id)
                
                if event.result.success:
                    session.mark_task_completed(task.task_id, event.result)
                    
                    # 子任务验收检查
                    sub_check = await self.validator.check_task(
                        task, event.result
                    )
                    if not sub_check.passed:
                        session.mark_task_needs_retry(task.task_id, sub_check.reason)
                else:
                    session.mark_task_failed(task.task_id, event.result.error)
            
            # 2. 整体验收检查
            overall_check = await self.validator.check_overall(
                plan.acceptance_criteria, session
            )
            
            if overall_check.passed:
                session.status = "accepted"
                break
            
            # 3. 未通过 -> AI分析原因，调整计划，进入下一轮
            adjustment = await self.planner.adjust_plan(
                plan, session, overall_check.failures
            )
            plan = adjustment.updated_plan
            
            await self.event_bus.emit("round_end", {
                "round": round_num,
                "status": "retry",
                "reason": overall_check.summary
            })
        
        # 生成最终报告
        report = await self.reporter.generate(session)
        return report
```

### 3.6 Validator（验收器）—— AI 驱动的验收确认

```python
class Validator:
    """
    多层验收机制:
    1. 规则验收 - 基于预定义的Checkpoint (数值比较、状态匹配)
    2. AI验收 - 调用AI判断是否满足自然语言描述的验收标准
    3. 交叉验证 - 用不同模型验证关键结果
    """
    
    async def check_task(self, task: TaskNode, result: ActionResult) -> ValidationResult:
        """子任务验收"""
        failures = []
        
        # 规则验收
        for cp in task.acceptance.checkpoints:
            if cp.check_type == "value_match":
                actual = self._extract_field(result.data, cp.field)
                if actual != cp.expected:
                    failures.append(f"{cp.field}: expected {cp.expected}, got {actual}")
            elif cp.check_type == "count_gte":
                actual = self._extract_field(result.data, cp.field)
                if actual < cp.expected:
                    failures.append(f"{cp.field}: expected >= {cp.expected}, got {actual}")
            elif cp.check_type == "status_equals":
                if result.data.get("status") != cp.expected:
                    failures.append(f"status: expected {cp.expected}, got {result.data.get('status')}")
            elif cp.check_type == "custom_ai_judge":
                # AI判断
                judgment = await self._ai_judge(task, result, cp)
                if not judgment.passed:
                    failures.append(judgment.reason)
        
        return ValidationResult(
            passed=len(failures) == 0,
            failures=failures
        )
    
    async def check_overall(self, criteria: AcceptanceCriteria, session: ExecutionSession) -> ValidationResult:
        """
        整体验收 - 使用AI对整个执行结果进行综合评判
        关键结果用交叉验证（不同模型）
        """
        # 汇总所有任务执行结果
        summary = session.get_summary()
        
        # AI综合评判
        judgment = await self.model_router.call(
            task_type="validation",
            system_prompt=VALIDATOR_SYSTEM_PROMPT,
            user_prompt=self._build_validation_prompt(criteria, summary)
        )
        
        # 交叉验证关键指标
        if self._has_critical_metrics(summary):
            cross_result = await self.model_router.cross_validate(
                task_type="validation",
                prompt=self._build_cross_validation_prompt(summary),
                models=["deepseek", "openai"],
                strategy="consensus"
            )
            if not cross_result.agreed:
                return ValidationResult(passed=False, 
                    failures=["交叉验证未达成共识: " + cross_result.details])
        
        return self._parse_judgment(judgment)
```

### 3.7 Task State Machine（任务状态机）

```
                    ┌──────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │ dispatch
                    ┌────▼─────┐
              ┌─────│ RUNNING  │─────┐
              │     └────┬─────┘     │
              │          │           │
         error│    success│      captcha│
              │          │           │
         ┌────▼───┐ ┌───▼────┐ ┌───▼─────┐
         │ FAILED │ │CHECKING│ │ PAUSED  │
         └────┬───┘ └───┬────┘ └───┬─────┘
              │         │          │ resume
         retry│    pass │ fail│    │
              │         │     │    │
              │    ┌────▼──┐  │    │
              │    │ACCEPTED│  │    │
              │    └───────┘  │    │
              │               │    │
              └───────┬───────┘    │
                      │            │
                 ┌────▼─────┐      │
                 │ RETRYING │◄─────┘
                 └────┬─────┘
                      │ (回到RUNNING)
                      ▼
               超过最大重试次数
                 ┌────▼─────┐
                 │TERMINATED│
                 └──────────┘
```

## 四、浏览器池（Browser Pool）

将现有的单浏览器同步模式改造为多浏览器异步池：

```python
class BrowserPool:
    """
    管理多个Playwright浏览器实例
    - 预创建可配置数量的浏览器
    - 按需分配，用完回收
    - 健康检查和自动重启
    """
    def __init__(self, config: BrowserPoolConfig):
        self.max_browsers: int = config.max_browsers  # 最大浏览器数
        self.pool: Dict[str, BrowserInstance] = {}
        self.available: asyncio.Queue = asyncio.Queue()
        self.playwright = None
    
    async def initialize(self):
        """启动时预创建浏览器"""
        self.playwright = await async_playwright().start()
        for i in range(self.config.initial_browsers):
            instance = await self._create_browser()
            self.pool[instance.id] = instance
            await self.available.put(instance.id)
    
    async def acquire(self, timeout: float = 30) -> BrowserInstance:
        """获取一个可用浏览器（如果没有就等待或创建新的）"""
        try:
            browser_id = await asyncio.wait_for(
                self.available.get(), timeout=timeout
            )
            instance = self.pool[browser_id]
            if not await instance.health_check():
                instance = await self._recreate(browser_id)
            instance.status = "active"
            return instance
        except asyncio.TimeoutError:
            if len(self.pool) < self.max_browsers:
                return await self._create_browser(status="active")
            raise ResourceExhaustedError("No browser available")
    
    async def release(self, browser_id: str):
        """归还浏览器"""
        instance = self.pool[browser_id]
        # 清理页面状态
        await instance.cleanup_pages()
        instance.status = "idle"
        await self.available.put(browser_id)
    
    async def shutdown(self):
        """关闭所有浏览器"""
        for instance in self.pool.values():
            await instance.close()
        await self.playwright.stop()
```

## 五、Web 界面架构

### 5.1 后端 API 设计 (FastAPI)

```
POST   /api/session/create          # 创建新的任务会话
POST   /api/session/{id}/request    # 提交用户需求
GET    /api/session/{id}/plan       # 获取AI生成的执行计划
POST   /api/session/{id}/confirm    # 用户确认验收标准
POST   /api/session/{id}/start      # 开始执行
POST   /api/session/{id}/stop       # 中止执行
GET    /api/session/{id}/status     # 获取执行状态
GET    /api/session/{id}/report     # 获取最终报告
WS     /ws/session/{id}             # WebSocket实时事件流

GET    /api/modules                 # 获取所有已注册模块
GET    /api/modules/{id}/capability # 获取模块能力描述
GET    /api/models                  # 获取已配置的AI模型列表
PUT    /api/models/routes           # 修改模型路由配置

GET    /api/browsers/status         # 浏览器池状态
GET    /api/browsers/{id}/screenshot # 浏览器截图
```

### 5.2 WebSocket 实时事件

通过 WebSocket 推送给前端的事件类型：

```python
class EventType(str, Enum):
    PLAN_READY = "plan_ready"              # 执行计划已生成
    PLAN_MODIFIED = "plan_modified"        # 计划被AI调整
    ROUND_START = "round_start"            # 新一轮执行开始
    ROUND_END = "round_end"               # 一轮执行结束
    TASK_START = "task_start"             # 子任务开始
    TASK_PROGRESS = "task_progress"       # 子任务进度更新
    TASK_COMPLETED = "task_completed"     # 子任务完成
    TASK_FAILED = "task_failed"           # 子任务失败
    VALIDATION_START = "validation_start" # 验收开始
    VALIDATION_RESULT = "validation_result" # 验收结果
    CAPTCHA_DETECTED = "captcha_detected" # 验证码检测
    BROWSER_EVENT = "browser_event"       # 浏览器事件
    FINAL_REPORT = "final_report"         # 最终交付报告
    ERROR = "error"                       # 系统错误
```

### 5.3 前端页面结构

```
/ (Dashboard)
├── 新建任务面板
│   ├── 需求输入区（富文本/Markdown）
│   ├── 历史需求快速选择
│   └── 提交按钮
│
├── 计划确认面板（用户确认验收标准后才显示）
│   ├── 任务DAG可视化（节点图）
│   ├── 验收标准列表（可编辑）
│   ├── 风险评估展示
│   ├── 预估时间
│   └── 确认/修改按钮
│
├── 执行监控面板
│   ├── 整体进度条
│   ├── 当前轮次 / 总轮次
│   ├── 任务列表 + 状态（实时更新）
│   ├── 浏览器实时截图（多个）
│   ├── 实时日志流
│   └── 紧急中止按钮
│
├── 结果交付面板
│   ├── 执行摘要（成功/失败统计）
│   ├── 验收报告
│   ├── 详细操作记录表
│   └── 导出功能（CSV/JSON）
│
└── 设置页
    ├── AI模型配置（多模型管理）
    ├── 模型路由表配置
    ├── 浏览器池配置
    └── 账号管理
```

## 六、完整用户流程

```
用户                          系统                          AI
 │                              │                            │
 │  1. 输入原始需求              │                            │
 │  "搜索关键词[Python教程],     │                            │
 │   对最近3天的视频发评论,      │                            │
 │   评论要自然,每个视频不重复"  │                            │
 │─────────────────────────────>│                            │
 │                              │  2. 发送给Planner           │
 │                              │───────────────────────────>│
 │                              │                            │
 │                              │  3. Planner读取Module能力   │
 │                              │  生成ExecutionPlan:         │
 │                              │  T1: auth.login_with_cookies│
 │                              │  T2: search.search_videos   │
 │                              │      (keyword="Python教程", │
 │                              │       time_range=3天,       │
 │                              │       max_count=20)         │
 │                              │  T3: history.check_visited  │
 │                              │      (批量去重)              │
 │                              │  T4: ai_filter.batch_filter │
 │                              │      (criteria=相关性)       │
 │                              │  T5: ai_gen.generate_comment│
 │                              │      (每个视频独立)          │
 │                              │  T6: comment.post_comment   │
 │                              │      (逐个发布)              │
 │                              │  T7: history.mark_visited   │
 │                              │                            │
 │                              │  验收标准:                   │
 │                              │  - 至少成功评论5条           │
 │                              │  - 评论内容不重复            │
 │                              │  - 无captcha触发             │
 │                              │<───────────────────────────│
 │                              │                            │
 │  4. 展示计划和验收标准        │                            │
 │  (DAG图 + 标准列表)          │                            │
 │<─────────────────────────────│                            │
 │                              │                            │
 │  5. 用户确认 (可修改标准)    │                            │
 │─────────────────────────────>│                            │
 │                              │                            │
 │                              │  6. Executor开始执行        │
 │                              │  ═══ Round 1 ═══           │
 │                              │  分配浏览器 -> 登录 ->      │
 │                              │  搜索 -> 筛选 -> 生成评论   │
 │                              │  -> 发布评论                │
 │  7. 实时WebSocket事件推送     │                            │
 │  (进度、截图、日志)           │                            │
 │<════════════════════════════>│                            │
 │                              │                            │
 │                              │  8. 验收检查                │
 │                              │  Validator评估结果:         │
 │                              │  - 成功3条 (未达5条目标)    │
 │                              │  - 触发1次captcha           │
 │                              │───────────────────────────>│
 │                              │  9. AI分析: 增加延迟,       │
 │                              │     先warmup再继续          │
 │                              │<───────────────────────────│
 │                              │                            │
 │                              │  ═══ Round 2 ═══           │
 │                              │  warmup -> 继续评论 ->      │
 │                              │  验收: 累计6条成功, 通过!   │
 │                              │                            │
 │  10. 收到最终交付报告         │                            │
 │  (摘要 + 详细记录 + CSV)     │                            │
 │<─────────────────────────────│                            │
 │                              │                            │
```

## 七、项目目录结构（新增部分）

```
bili-comment-assistant/
├── [现有文件保持不变]
│
├── modules/                        # 功能模块层（重构自core/）
│   ├── __init__.py
│   ├── base.py                     # IModule基类, ActionResult, ModuleCapability等
│   ├── registry.py                 # ModuleRegistry 模块注册中心
│   ├── auth_module.py              # 认证模块 (封装core/auth.py)
│   ├── search_module.py            # 搜索模块 (封装core/search.py)
│   ├── comment_module.py           # 评论模块 (封装core/comment.py)
│   ├── warmup_module.py            # 养号模块 (封装core/warmup.py)
│   ├── ai_gen_module.py            # AI生成模块 (封装core/ai_manager.py的评论生成)
│   ├── ai_filter_module.py         # AI筛选模块 (封装core/ai_manager.py的筛选)
│   ├── history_module.py           # 历史记录模块 (封装core/history.py)
│   ├── captcha_module.py           # 验证码模块 (封装core/captcha_*.py)
│   ├── config_module.py            # 配置模块 (封装core/config.py)
│   ├── notify_module.py            # 通知模块 (封装core/notifier.py)
│   ├── report_module.py            # 报告模块 (新建)
│   └── browser_pool.py             # 浏览器池模块 (新建)
│
├── ai_center/                      # AI中控台核心
│   ├── __init__.py
│   ├── planner.py                  # 规划器 - 需求拆解与验收标准生成
│   ├── dispatcher.py               # 调度器 - DAG任务调度 + 资源分配
│   ├── executor.py                 # 执行引擎 - 多轮循环执行
│   ├── validator.py                # 验收器 - 规则+AI双重验收
│   ├── reporter.py                 # 报告器 - 结果汇总与交付
│   ├── model_router.py             # 模型路由器 - 多模型管理与任务分配
│   ├── state_machine.py            # 任务状态机 (FSM)
│   ├── event_bus.py                # 事件总线 (WebSocket推送)
│   ├── prompts/                    # AI中控台专用prompt模板
│   │   ├── planner_prompts.py      # 规划器prompt
│   │   ├── validator_prompts.py    # 验收器prompt
│   │   └── adjustment_prompts.py   # 计划调整prompt
│   └── models/                     # 数据模型
│       ├── plan.py                 # ExecutionPlan, TaskNode等
│       ├── session.py              # ExecutionSession
│       └── events.py               # 事件类型定义
│
├── web/                            # Web界面
│   ├── app.py                      # FastAPI主应用
│   ├── routers/                    # API路由
│   │   ├── session_router.py       # /api/session/* 
│   │   ├── module_router.py        # /api/modules/*
│   │   ├── model_router_api.py     # /api/models/*
│   │   └── browser_router.py       # /api/browsers/*
│   ├── websocket/
│   │   └── ws_handler.py           # WebSocket连接管理
│   └── frontend/                   # 前端静态文件
│       ├── index.html
│       ├── css/
│       ├── js/
│       └── components/
│
├── core/                           # [保持现有] 底层实现
├── gui.py                          # [保持现有] 桌面GUI
├── gui_tabs/                       # [保持现有]
├── main.py                         # [保持现有] 桌面GUI的后端
├── utils/                          # [保持现有]
└── server/                         # [保持现有] 调试服务器
```

## 八、扩展性设计

### 8.1 新增功能模块的方法

- 创建新文件 `modules/xxx_module.py`
- 实现 `IModule` 接口，定义 `get_capability()` 返回能力描述
- 在 `ModuleRegistry` 中注册即可
- AI 会自动通过 `get_capability()` 了解新模块并在规划时使用它

示例：未来新增一个「私信模块」：

```python
class DirectMessageModule(IModule):
    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="direct_message",
            description="向Bilibili用户发送私信",
            actions=[
                ActionSpec(
                    name="send_message",
                    description="向指定用户发送私信",
                    parameters={"user_id": ParamSpec(type="string", ...), "text": ParamSpec(...)},
                    returns={"status": "success/failed"},
                    risk_level="high"
                )
            ],
            requires_browser=True,
            requires_auth=True,
            category="browser_automation"
        )
```

### 8.2 新增 AI 模型的方法

只需在配置中添加新的 provider 和路由规则：

```yaml
providers:
  claude:
    base_url: "https://api.anthropic.com/v1"
    api_key: "..."
    model: "claude-3-sonnet"
routes:
  planning:
    primary_model: "claude"
    fallback_model: "deepseek"
```

## 九、1.0 版本范围与优先级

| 优先级 | 组件 | 说明 |
|--------|------|------|
| P0 | modules/base.py + registry.py | 模块接口标准和注册中心 |
| P0 | 12个功能模块封装 | 从现有 core/ 包装为 `IModule` |
| P0 | ai_center/planner.py | 需求拆解 |
| P0 | ai_center/executor.py | 执行引擎 |
| P0 | ai_center/validator.py | 验收器 |
| P0 | ai_center/model_router.py | 多模型路由 |
| P0 | modules/browser_pool.py | 多浏览器管理 |
| P0 | web/app.py + WebSocket | 最小 Web 界面 |
| P1 | ai_center/dispatcher.py | DAG 调度 |
| P1 | ai_center/reporter.py | 交付报告 |
| P1 | 前端完整 UI | Dashboard + 监控面板 |
| P1 | 交叉验证 | 多模型验证关键结果 |
| P2 | 历史会话管理 | 查看历史执行记录 |
| P2 | 高级路由配置 UI | 可视化配置模型路由 |

## 十、技术选型总结

| 组件 | 技术 | 理由 |
|------|------|------|
| 异步框架 | asyncio + FastAPI | 支持并行浏览器+并行 AI 调用 |
| 浏览器自动化 | Playwright async API | 从 sync 迁移到 async，支持并行 |
| Web 后端 | FastAPI | 已有依赖，async 原生支持，WebSocket 内置 |
| 实时通信 | WebSocket | 双向通信，实时推送执行事件 |
| AI SDK | openai (async) | 统一 OpenAI-compatible 接口 |
| 数据模型 | Pydantic v2 | 类型安全，JSON 序列化，FastAPI 原生支持 |
| 任务调度 | asyncio.TaskGroup | Python 3.11+ 原生并发 |
| 前端 | 轻量 HTML+JS (1.0) | 1.0 快速验证，后续可换 Vue/React |
| 状态持久化 | SQLite (via aiosqlite) | 会话历史、执行记录，轻量无需额外服务 |

以上就是完整的架构规划。核心设计要点总结：

- **模块化封装**：现有 12 个功能模块全部通过统一的 `IModule` 接口封装，每个模块自描述能力（`get_capability()`），AI 可以自动理解并调用
- **AI 中控台 5 大核心组件**：Planner(规划) → Dispatcher(调度) → Executor(执行循环) → Validator(验收) → Reporter(交付)，形成闭环
- **多模型路由**：按任务类型分配模型（规划用 DeepSeek、验收用 GPT、生成用 Qwen 等），关键结果用不同模型交叉验证
- **多轮自主执行**：最多 10 轮循环，每轮执行后 AI 验收，未通过则分析原因、调整计划、下一轮重试，直到满足用户确认的验收标准
- **多浏览器并行**：`BrowserPool` 管理多个 Playwright async 实例，DAG 调度器自动并行执行无依赖的任务
- **扩展性**：新增功能模块只需实现接口并注册，新增 AI 模型只需添加配置，AI 会自动发现并使用