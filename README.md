# 移动声测等效暴露拼接

环境声测数据整理员使用的离线数据处理服务。提交同一测线时轴上的短段声级与校准记录，按时段择取有效来源并以能量整合，显式列出覆盖缺口。

| 入口 | 工作流 | 样例结果 | 合成输入 |
| --- | --- | --- | --- |
| `POST /soundstrip/exposure` | 拼接单条巡测并归约声暴露 | 窗口内有效 5000 毫秒而不是 8000，等效级约 56.63 dB | [`exposure.json`](examples/exposure.json) |
| `POST /soundstrip/compare` | 计算两次巡测共同覆盖上的声级差 | 仅 4000 毫秒双侧共用，右减左约 −7.40 dB | [`compare.json`](examples/compare.json) |
| `POST /soundstrip/coverage` | 导出拒用、缺口和择取证据 | 冲突、缺口、无证书的来源分别可见 | [`coverage.json`](examples/coverage.json) |
| `POST /soundstrip/peak` | 从巡测区间选出等效级最高的定长窗口 | 0–10 毫秒、窗长 4 毫秒时峰值窗为 `[4, 8)`，整窗由备机证书支持，约 68.75 dB | [`peak.json`](examples/peak.json) |
| `POST /soundstrip/window` | 复核指定起点的定长窗口为何可用或不可用 | `[4, 8)` 可用，贡献读数为 `B0`、`B1`，证书 `C-BACKUP` | [`window.json`](examples/window.json) |

定长窗口规则：一个窗口只由同一台仪器的同一份有效证书支持；窗内各片段都须有该仪器的有效读数，同机重叠按原优先级择取，任一未决并列都使该仪器不能支持该窗。在其余能完整支持该窗的仪器中，比较各自窗内最弱一段获选读数的优先级，并列第一则该窗有争议、不参评。`peak` 的候选起点取自读数与证书边界（不逐毫秒试遍时轴），等效级最高者入选，相同则取最早。结果携带实际证书与贡献读数；无可用窗时区分 `insufficient_observation`（连续观测或证书不足）与 `priority_dispute`（读数完整但优先级争议）。

使用 Python 3.10+ 标准库，无需安装依赖；无需数据库、账户或外部服务。

```sh
python3 -B -m soundstrip.app --port 8824
```

运行于 `127.0.0.1:8824`，`GET /health` 列出操作。可以用另一终端向服务发送样例：

```sh
curl -sS -H 'Content-Type: application/json' --data-binary @examples/exposure.json http://127.0.0.1:8824/soundstrip/exposure
```

不启动监听器也可以从项目根目录复核生产 WSGI 入口，以下各命令同时核对可预期输出及拒绝表示：

```sh
python3 -B -m examples.check exposure
python3 -B -m examples.check compare
python3 -B -m examples.check coverage
python3 -B -m examples.check peak
python3 -B -m examples.check window
```

本仓不含自动化测试套件；上述命令为公开示例和有界工作流检查。字段、规则和限制见 [PROJECT_SPEC.md](PROJECT_SPEC.md)。
