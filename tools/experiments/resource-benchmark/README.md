# 资源测量（独立实验）

测量依赖与主程序分开：`python -m pip install -r tools/experiments/resource-benchmark/requirements.txt`。
从仓库根目录执行，需连接 UESTC，Windows WLAN 服务和访问权限必须可用：

```powershell
python tools/experiments/resource-benchmark/measure.py --backend baseline --mode night --scenario online --duration 600
python tools/experiments/resource-benchmark/measure.py --backend native --mode night --scenario online --duration 600
python tools/experiments/resource-benchmark/measure.py --backend baseline --mode night --scenario logout --duration 60
python tools/experiments/resource-benchmark/measure.py --backend native --mode night --scenario logout --duration 60
```

持续模式改为 `--mode continuous`，至少运行90秒。默认间隔严格沿用5秒/30秒，logout在测量中点模拟认证失效。实际WLAN查询＋本机loopback HTTP模拟认证门户，不读取凭据、不真实登出、只向127.0.0.1发送模拟HTTP请求，不发送校园网认证请求、不修改任务。state_queries/login_requests/http_requests 由loopback服务实际收到的HTTP请求计数。恢复时间包含轮询等待与登录保护查询，包含本机HTTP往返，不能代表真实门户服务端耗时。

baseline 从固定提交8809b05读取旧检测函数，主程序不包含备用netsh。CPU父进程与子进程分别测量，RSS同样分列，不能将峰值相加当作同步总峰值；计数排除Git读取与预热。在线与登出场景应分别比较，保持网络与负载条件一致，长时间建议600秒或以上。日志只输出一条汇总，无逐次在线日志。CPU为Windows累计计时，短测量的0表示低于计时分辨率。

测量结果放 `results/`（Git忽略），不得上传凭据或原始用户日志。真实睡眠、Wi-Fi切换和任务账户验收见[验收说明](../../../docs/RESOURCE-OPTIMIZATION.md)。
