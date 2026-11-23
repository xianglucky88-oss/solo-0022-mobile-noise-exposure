# 移动声测等效暴露拼接

环境声测数据整理员使用的离线数据处理服务。提交同一测线时轴上的短段声级与校准记录，按时段择取有效来源并以能量整合，显式列出覆盖缺口。

| 入口 | 工作流 | 样例结果 | 合成输入 |
| --- | --- | --- | --- |
| `POST /soundstrip/exposure` | 拼接单条巡测并归约声暴露 | 窗口内有效 5000 毫秒而不是 8000，等效级约 56.63 dB | [`exposure.json`](examples/exposure.json) |
| `POST /soundstrip/compare` | 计算两次巡测共同覆盖上的声级差 | 仅 4000 毫秒双侧共用，右减左约 −7.40 dB | [`compare.json`](examples/compare.json) |
| `POST /soundstrip/coverage` | 导出拒用、缺口和择取证据 | 冲突、缺口、无证书的来源分别可见 | [`coverage.json`](examples/coverage.json) |

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
```

本仓不含自动化测试套件；上述命令为公开示例和有界工作流检查。字段、规则和限制见 [PROJECT_SPEC.md](PROJECT_SPEC.md)。
