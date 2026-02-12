# paradex
多账户统计助手
🚀 Paradex PnL Reader - Season 2 Ultimate Edition (v5.2)
Paradex PnL Reader 是一款专为 Paradex 交易者设计的资产管理与统计工具。它能够高效地跨账户聚合交易数据，实时监控盈亏、交易量及 XP 增长情况，并支持一键导出生产级 Excel 报表。

🌟 v5.2 核心更新说明
[核心修复] 统一地址查询逻辑： 优化为单次 API 调用，彻底解决因频繁请求导致 Excel 中账户地址显示为空的问题。

[配置优化] 分组逻辑重置： 重新清理 GROUPS 配置，消除账户重复显示问题。

[功能增强] 自动化报表： 保持 Excel 自动导出功能，并支持完整的账户地址记录。

🛠️ 核心功能
📊 实时资产汇总： 一键获取全账户余额、净充值、总盈亏及资金利用效率（$/M）。

📅 周报自动化： 自动计算上周（UTC 周五至周五）的成交额、盈亏及笔数。

⭐ XP 深度追踪： 监控 Season 2 的 Earned XP、Available XP 以及最新周的 XP 增量。

📈 持仓实时监控： 扫描所有账户的活动仓位、方向、入场价及未结盈亏 (uPnL)。

💾 Excel 一键导出： 自动生成包含完整地址和详细数据的 .xlsx 统计报表。

🤖 Telegram 推送： 支持将汇总统计数据实时推送到指定的 Telegram 频道。

📦 环境准备
安装依赖库：

Bash
pip install requests python-dotenv pandas openpyxl
配置文件： 在脚本同级目录下创建 para.env 文件，并填入你的 API Key 和配置信息：

Code snippet
PARADEX_API_KEY_0_1=你的API_KEY
PARADEX_API_KEY_0_2=...
TG_BOT_TOKEN=...
TG_CHAT_ID=...
🚀 快速开始
运行主程序启动 GUI 界面：

Bash
python query.py
操作指南：

总资金： 查看历史累计统计，并触发 Telegram 推送。

最新周报： 生成统计并自动在 reports/ 文件夹下保存 Excel 文件。

本周表现： 查看从上周五（UTC）至今的实时交易表现。

持仓监控： 检查是否有未平仓位。

⚠️ 安全与配置提示

代理设置： 默认配置了 127.0.0.1:10808 的 HTTP 代理。如需更改或关闭，请修改脚本中的 PROXY_CONFIG。

数据缓存： 交易数据会增量缓存于 logs/stats_cache.json，以减少 API 负载并加快查询速度。

API 限制： v5.2 已优化查询频率，但建议在管理超大规模账户组（20+ 账户）时合理点击刷新。

📂 目录结构
query.py: 主程序

para.env: API 密钥存储 (需自行创建)

logs/: 交易数据增量缓存

reports/: 导出的 Excel 报表

README.md: 项目文档
