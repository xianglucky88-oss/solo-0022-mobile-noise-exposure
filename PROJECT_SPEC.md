# 移动声测等效暴露拼接 · 数据与接口规范

## 使用者和交付

使用者：环境声测数据整理员。提交同一测线时轴上的短段声级与校准记录，按时段择取有效来源并以能量整合，显式列出覆盖缺口。 所有样例为合成数据。服务无跨请求状态或数据持久化，不连接外部接口。

## 规则和输入

- 请求内已处于同一合成毫秒时轴，所有 `[start,stop)` 左闭右开。证书 `certificates` 含 `id,instrument,start,stop,offset_db`；同一仪器的证书有效期不重叠。读数 `readings` 含 `id,instrument,start,stop,db,priority`，优先级数字越大越优先。输入声级在给定此段内按常值处理。
- `coverage` 按窗口、读数和相关证书边界切片，返回原始读数及有效证书。合法候选按优先级择取，并列最高拒选；没证书与没读数分别记录。高优先级但无证书不挡住已证实的低优先级来源。
- `exposure` 根据获接受部分的声能与实际覆盖长度换算等效声级，无覆盖为 `null`。`compare` 的 `left` 与 `right` 是时轴已对齐的两份巡测，差值用共同有效时间上右侧与左侧的声能比计算，零共同覆盖时差值为 `null`。不假设未测区域安静，不作实地合规结论。

## 入口和可观察结果

| 入口 | 工作流 | 样例结果 | 合成输入 |
| --- | --- | --- | --- |
| `POST /soundstrip/exposure` | 拼接单条巡测并归约声暴露 | 窗口内有效 5000 毫秒而不是 8000，等效级约 56.63 dB | [`exposure.json`](examples/exposure.json) |
| `POST /soundstrip/compare` | 计算两次巡测共同覆盖上的声级差 | 仅 4000 毫秒双侧共用，右减左约 −7.40 dB | [`compare.json`](examples/compare.json) |
| `POST /soundstrip/coverage` | 导出拒用、缺口和择取证据 | 冲突、缺口、无证书的来源分别可见 | [`coverage.json`](examples/coverage.json) |

`POST` 接收不大于 512 KiB 的 UTF-8 JSON，要求 `application/json`。字段缺失、主键重复、非法范围或冲突合同返回 HTTP 400。可合法表达的未解业务状态仍为 HTTP 200。健康接口为 `GET /health`。

## 代码职责

- `soundstrip/app.py`：注册该服务公开数据入口。
- `soundstrip/http_service.py`：限定请求方法、内容体积和 JSON 传输边界。
- `soundstrip/contract.py`：严格字段、范围及标识去重。
- `soundstrip/calibration.py`：证书生效边界。
- `soundstrip/splice.py`：多源优先级仲裁。
- `soundstrip/exposure.py`：时间加权声能。

请求由 WSGI 入口分发给对应领域归约，边界字段由校验层及领域解析器检查；证据随归约返回，不作为后置猜测。对外入口的运行步骤和输出核对见 README。单元测试留置；不含故障预埋、私有评审或后续任务解法。
