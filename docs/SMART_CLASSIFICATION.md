# 智能推荐分类（实验性）

> 2026-10-25 起采用词库匹配＋本地模型排序＋多候选选择，最新实现和评估见 [混合分类说明](HYBRID_CLASSIFICATION.md)。下文保留历史单候选版本的准备方法与评估，不能当作当前效果或交互说明。

## 使用与边界

发布、编辑商品时填写具体商品标题，点击“智能推荐分类”，检查建议后点击“使用此分类”。这一步只修改表单，点击发布或保存才修改商品。商品描述选填，仍用于展示和现有搜索，不参与推理。
可以始终手动选择分类。标题变化、手动改分类、关闭弹窗、切换商品会丢弃旧建议及过期请求结果；仅修改描述不会使建议失效。模型失败、忙碌或前端等待超过 45 秒时不阻断手动操作。

只验证并使用 mDeBERTa，未下载 BGE。商品分类沿用原列表/编辑页面的 10 类；发布页面由原有 6 个选项补齐到同一组既有分类。没有新增业务类别，没有自动重写历史数据。首页和左上角品牌文字未改动。

## 模型与实现

- 来源：[MoritzLaurer/mDeBERTa-v3-base-mnli-xnli](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli)。保留模型下载目录中的官方 README、来源及 MIT 声明。
- 固定版本：`8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c`。
- 使用标准 Transformers / PyTorch CPU 推理，`trust_remote_code=False`，仅加载 safetensors，不加载 pickle 权重。
- `models/mdeberta` 保存模型，权重 557,652,046 字节，模型目录文件合计约 579 MB（十进制）；依赖、运行内存需额外空间。模型不放入源码和备份压缩包。
- `/api/v1/items/category-suggestion`：POST，要求现有 JWT 登录且用户仍存在。只读建议，无商品写入或数据库迁移。
- 分类接口只读取标题，最长 50 字符；兼容旧客户端但忽略额外传来的描述。规范化标题空白，推理时文本对最多 256 token，仅截断商品标题而保留候选假设。商品描述选填，非空最多 500 字符；数据库仍使用非空字符串存储，原有数据不变。
- NLI 模板为“这段文字描述的是{label}。”，候选短语和业务类别一一对应。另有天气、求助、招聘、闲聊、信息不明确等拒绝候选，不映射为业务“其他”。
- 在候选之间计算相对蕴含分数，同时检查蕴含/矛盾支持分数及前两名分差。分数不是正确概率，因此不在 UI 显示百分比。
- 每个 Flask 应用实例持有一个服务对象，首次推理加载，此后进程内复用。每个服务实例最多执行一个推理，忙碌请求返回 429；加载失败短暂冷却后可重试。多工作进程会各自占用模型内存。
- 网络下载只由显式准备脚本执行，推理加载设置 `local_files_only=True`。评估进一步禁止 socket 连接，已验证离线推理。
- 前端取消/超时不会杀掉服务器正在计算的任务；锁会保留到真实推理结束，不会因客户端取消而放开计算并发。当前没有强制杀死卡住推理的进程隔离机制；异常卡住时需重启自己启动的服务。
- 普通网站健康检查不加载模型。启动器核对 `category-suggestion-title-v2` 能力标记，避免复用旧 API；该标记表示代码支持接口，不代表模型已经加载。

## 本机准备与迁移

本机已安装，模型已下载。其他 Windows 机器在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe scripts/prepare_classifier.py
.\.venv\Scripts\python.exe scripts/evaluate_classifier.py --split test
```

仅使用官方 PyTorch、PyPI 和 Hugging Face；无需 GPU、不使用外部推理 API。如果下载被网络限制阻止，应解决官方来源访问，不要使用未知镜像。模型缓存可能额外占空间。

继续双击根目录 `启动.bat`。先关闭自己以前启动的旧窗口，或让启动器自动避开旧端口；不要结束未知进程。访问地址看窗口中的 `Frontend:`，本次检查使用 3001、后端 5001，不能保证下次相同。

配置来自 `.env`（修改后重启）：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| CLASSIFICATION_ENABLED | true | false 时返回不可用，手动分类仍可用 |
| CLASSIFICATION_MODEL_PATH | 项目/models/mdeberta | 本地模型文件夹 |
| CLASSIFICATION_THREADS | 2 | CPU 线程数，建议保持正整数 |
| CLASSIFICATION_MIN_SCORE | 0.45 | 相对候选分数下限 |
| CLASSIFICATION_MIN_SUPPORT | 0.70 | 蕴含/矛盾支持分数下限 |
| CLASSIFICATION_MIN_MARGIN | 0.25 | 前两名分差下限 |

类别说明、NLI 短语在 `app/services/classification.py`，界面既有类别在 `frontend/src/constants/itemCategories.js`。变更分类体系必须重新验证映射与评估，不要只改一侧。若调整阈值，应使用开发集，另收集独立测试集。

## 评估结果及限制

### 当前标题版（2026-10-23）

当前接口只使用商品标题。新建的 `tests/data/classification_titles.json` 含 24 条由 Agent 编写的合成标题（20 条有商品类别、4 条不明确或非商品），每条有独立 `title` 字段；没有将原有完整描述改名为标题。评估明细保存在 `docs/classification-evaluation-title-test.json`。这组标题不是独立真人标注数据，也未保证与先前开发样本完全独立，不能据此推断真实用户准确率。

在未改模型、模板和阈值的条件下，20 条商品标题 Top-1 准确率 40%，macro-F1 约 0.397；24 条样本中推荐 14 条，覆盖率 58.3%，其中 7 条正确（50%）。短标题中乐器、工具、玩具等类别存在明显误分。预热后单条中位推理约 0.50 秒，首次加载约 6.12 秒。用户仍需确认推荐；不要以此数字宣称标题版更准确。

### 历史标题＋描述版本（仅供回溯）

没有用户人工标注数据。本次 60 条文本全部为 Agent 合成，明确标记 `source=agent_synthetic`：14 条开发样本、46 条留出样本（40 条可分类商品、6 条无关/不明/跨类别文本）。没有读取用户商品来生成样本，没有训练模型。

开发过程中发现长描述模板混淆严重，改用短语，并加入拒绝候选；分差由 0.15 调整为 0.25 以减少开发集中的跨类别误推荐。保留早期开发结果文件，最终测试集评估后未据其调参。样本少、作者相同、部分商品与类别说明的例子相近，属于冒烟检查，不代表独立真实世界性能。

以下历史结果来自旧的完整文本输入，不代表当前标题版效果；原评估文件 `classification-evaluation-test.json` 未被覆盖（逐条结果、类别精确率/召回率/F1均保留）：

| 指标 | 结果 |
| --- | --- |
| 可分类商品 Top-1 准确率 | 22/40，55.0% |
| 可分类商品 macro-F1 | 0.556 |
| 全部文本推荐覆盖率 | 26/46，56.5% |
| 已推荐结果正确率 | 17/26，65.4% |
| 6 条无关/不明/跨类文本 | 均拒绝推荐；样本过少，不能保证普遍有效 |
| 加载耗时（含首次库导入） | 约 7.33 秒 |
| 预热后单条中位耗时 / P95 | 约 0.64 / 0.75 秒 |
| 评估进程结束前 RSS | 约 1662 MB，非峰值测量 |

环境：Windows、Python 3.12.10、PyTorch 2.6.0+cpu、Transformers 4.57.6，Intel64 Family 6 Model 204，31.5 GiB 内存，2 个推理线程。

明显限制：文具可能误分到家居或电子产品，电子琴可能误分电子产品，玩具与运动/艺术品混淆，“其他”覆盖不足。部分文本改写后可能从推荐变为拒绝推荐；浏览器初测的一条重复描述教材文本就被拒绝。不能将该模型作为自动裁决器，也不能宣称已经达到可靠商品分类水平。目前交付为可关闭、需用户确认的实验功能。

课程报告应写“基于预训练模型的商品智能分类应用”，如实展示错误案例及局限，不应写“自主训练大模型”或套用开发集的高分宣传。

## 验证与复现

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
& 'D:\Node.js\npm.cmd' --prefix frontend run build
& 'D:\Node.js\node.exe' launcher.js --check-startup
```

受限沙箱若无法写系统临时目录，可在项目创建 `tmp`，仅对当前终端设置 TEMP/TMP 指向它，不修改系统配置。测试使用独立内存/临时数据库。

`scripts/browser_classification.cjs` 为浏览器集成检查，使用独立初始化数据库和临时空闲端口，只关闭自己创建的进程。需要已有 Playwright 与 Chrome，设置 `PLAYWRIGHT_MODULE` 指向 Playwright 模块位置后运行 `node scripts/browser_classification.cjs`。真实预测测试与有意模拟的故障/延迟测试分别注明，模拟测试不替代真实推理验证。标题版评估运行 `.\.venv\Scripts\python.exe scripts/evaluate_classifier.py --input-type title`；旧版复核需显式添加 `--input-type legacy-text`，但会重新写入相应的旧文件，先另存一份。

未验证真实用户分布、大并发、多工作进程、所有浏览器和实体手机；不承诺生产级模型服务 SLA。

当前标题版实际检查：27 项后端测试通过；依赖一致性检查、前端构建和启动入口检查通过。Chrome 实际验证了真实模型经 Vite 代理只接收标题、确认后无描述发布、详情空状态和编辑保存；模拟延迟验证标题变化/手动分类/关闭弹窗后的响应失效，描述变化保持建议；模拟 503 后仍可手动分类并发布。桌面 1440px、移动视口 390px，未出现页面脚本异常。模型效果以完整标题样本评估文件为准，浏览器示例只用于交互验证。

## 备份、数据与恢复

标题版修改前新增源码基线：`C:\Users\sun\Documents\Codex\2026-10-22\qin\outputs\campus-loop-title-backup-20261023-182908\source.zip`。恢复时先关闭自己启动的服务，将压缩包解压至新空目录，与当前源码对比再恢复。本次未改数据库表结构，保留历史商品描述；设置 `CLASSIFICATION_ENABLED=false` 可临时关闭建议功能。备份排除了模型、依赖、运行数据库及缓存。

修改前源码压缩包：`C:\Users\sun\Documents\Codex\2026-10-22\qin\outputs\campus-loop-classification-backup-20261023-173023\source.zip`。
不是 Git 工作区，因此采用源码基线压缩包；排除依赖、数据库、构建产物、日志和模型。所有已有修改都包含在该基线中。

本次不需要数据库结构变更，未执行分类迁移；测试使用独立数据库。修改前实际数据库 SHA256：`17cd9f32bd29b72433923f88bd88f2f2b32fec033a4ca125e850b9e97be2a9b7`。
完成测试与启动检查后复核 SHA256 完全一致；备份 ZIP 完整性检查通过（95 个基线文件）。本次未写用户数据库，因此没有额外复制数据库；已有历史数据库备份仍保持原样。

恢复时先关闭自己启动的服务，将 source.zip 解压到一个新的空文件夹对比，再恢复所需源码。单纯覆盖不会去掉新增文件：需对照压缩包清单处理新增的分类服务、API、组件、脚本、测试及文档，不要递归删除项目。保留当前数据库，不用旧库覆盖新交易数据。最轻量回退是设置 `CLASSIFICATION_ENABLED=false` 并重启；不必卸载依赖或删除模型。
