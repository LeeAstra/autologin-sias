# 独立实验工具

此目录保存用于观察夜间认证失效的工具，和 `src/` 正式后台程序分开维护。不纳入正式安装包，不创建、更改或停用任何计划任务。

| 目录 | 用途 |
|---|---|
| [login-monitor](login-monitor/README.md) | 循环查询认证状态，失效后重登，记录每晚失效区间、次数和恢复耗时 |
| [resource-benchmark](resource-benchmark/README.md) | 真实WLAN查询与本机HTTP模拟门户的CPU、内存、子进程和恢复对照 |
| [login-diagnostics](login-diagnostics/README.md) | 单次调用正式登录流程，记录脱敏请求详情与前后状态 |

独立实验仅用于研究，不是普通用户安装步骤。实验监测额外查询、可能提交认证并阻止自动睡眠；先按工具说明手动隔离正式维护，再运行。监测版默认到下一次本地 08:00 结束。源码可直接运行；无需上传真实实验记录。完整测试和参数见各目录说明。

实验代码可以和正式代码放在同一个仓库，但不需要长期保留一条“实验分支”。用短期功能分支和 PR 合入 `main`；目录隔离区分用途，Release 标签标识版本，Windows CI 分别验证正式程序和实验工具。

构建时会打包当前 `src/` 版本，因此源码运行或重新构建和旧监测 EXE 可能不同。持续多晚对照时使用相同 EXE，保留本地 `BUILD-INFO.json` 和参数；不要在实验中途替换程序。循环工具额外执行独立门户查询和外网验证，兼容 CLI 无参数默认单次执行；v1.3.0 完整安装配置的正式任务使用所选维护循环。

`results/`、`.env`、EXE、spec、构建目录和本地构建记录均忽略，不提交到 Git。即使记录已经脱敏，也只在本机保存；需要公开复现时编写合成夹具，分享前人工检查。

维护者在仓库根运行：

```powershell
python -m unittest discover -s tools/experiments/login-diagnostics -v
python -m unittest discover -s tools/experiments/login-monitor -v
```
