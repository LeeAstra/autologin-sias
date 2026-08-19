# Changelog

## 1.1.0

- 增加 `AutoLogin_SIAS_Setup.exe` 首次配置向导。
- 支持安全输入密码并创建 `.env`。
- 增加 `--setup`、`--check`、`--version` 参数。
- 增加日志轮转和日志文件不可写时的兜底处理。
- 保留无参数静默模式，适合任务计划程序。
- 修正 EXE 与项目根目录 `.env` 的查找顺序。

## 1.0.0

- 首个无浏览器后台登录版本。
- 使用门户兼容的 RC4 密码转换和动态 `auth_tag`。
- 支持 `login.php` 与 `handler_checkjump` 请求流程。
