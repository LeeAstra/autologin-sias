# 安全漏洞反馈

本页面向发现安全漏洞的用户与研究者。普通 BUG、功能建议和使用问题提交[Issues](https://github.com/LeeAstra/autologin-sias/issues/new/choose)；安全漏洞不要在公开 Issue 中披露细节。

## 私下报告漏洞

本仓库已开启 GitHub 私密漏洞报告。打开仓库[Security 页面](https://github.com/LeeAstra/autologin-sias/security)，点击 **Report a vulnerability**，登录 GitHub 后私下提交；也可使用[私密报告入口](https://github.com/LeeAstra/autologin-sias/security/advisories/new)。

报告请包含：

- 受影响的程序版本及运行环境。
- 问题描述和预期行为。
- 最小复现步骤，优先使用合成数据。
- 可能的影响及范围。

**不得附带真实账号密码、`.env`、凭据备份或未脱敏日志。** Cookie、令牌、个人网络信息及抓包也需先移除敏感内容；私密渠道不需要真实校园账号。不要为了复现影响无关账户或网络。

## 安全更新支持范围

当前安全修复维护范围为最新正式版 **v1.3.0**；更早版本不承诺回补。报告可以涉及旧版，请注明版本，不要求先执行有风险的升级或测试。版本变化见[更新日志](CHANGELOG.md)。

不承诺固定响应或修复时限，也未设漏洞奖励。安全修复按维护与发布流程处理，不覆盖已经发布的安装包。

## 已知边界与配置保护

- `.env` 和安装备份可能保存明文凭据，JSON 编码不是加密；不要分享整个安装或备份目录。
- 门户使用 HTTP 和 RC4 兼容协议，不是现代加密传输；项目不能改变门户本身的安全性。
- 发布包未签名，SHA256 仅用于[校验完整性](docs/MAINTENANCE.md#校验下载文件)，不代表安全保证。
- 安装器通过 PowerShell 管理任务；[行为防护核查](docs/TROUBLESHOOTING.md#火绒或其他行为防护提示)不要求关闭防护或全目录加白。

若凭据已公开，先在校园门户修改密码，再按[使用指南](docs/USAGE.md#升级切换模式或更换凭据)更新配置及曾设置的环境变量，并检查旧副本和备份。删除公开帖子不能保证资料尚未被获取。
