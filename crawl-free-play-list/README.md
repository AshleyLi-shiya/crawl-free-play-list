# 四平台免费内容爬取工具

自动爬取芒果TV、爱奇艺、腾讯视频、优酷四大平台的免费电影和电视剧数据，进行男女频分类，生成 Excel 报告。

基于 [Qoder](https://qoder.com) Agent Skill 驱动，一条指令即可完成全流程。

## 前置条件

- Python 3.8+
- [Qoder CLI](https://qoder.com) 或 Qoder Work
- Browser MCP（优酷爬取需要）

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/crawl-free-content.git

# 2. 安装依赖
cd crawl-free-content
pip3 install -r requirements.txt

# 3. 在 Qoder 中打开此目录
qoder .

# 4. 输入触发词，例如：
#    "爬取四平台免费内容"
#    "更新四平台数据"
#    "生成免费内容Excel"
```

Qoder Agent 会自动读取 `.qoder/skills/crawl-free-content/SKILL.md`，按照 4 个阶段依次执行爬取、过滤、汇总、生成报告。

## 工作流

```
Phase 1  三平台并行爬取（芒果TV / 爱奇艺 / 腾讯视频）
Phase 1.5 腾讯视频 VIP 二次过滤
Phase 2  优酷列表爬取（需 Browser MCP）
Phase 3  优酷详情补充
Phase 4  四平台汇总 + 性别分类 + Excel 生成
```

## 输出

- 位置：`output/四平台免费内容详情-{YYYYMMDD}.xlsx`
- Sheet1「全部详情」：平台、类型、剧名、年份、演员、地区、集数、题材、男女频
- Sheet2「汇总统计」：各平台电视剧/电影数量及男女频分布

## 目录结构

```
crawl-free-content/
├── .qoder/skills/crawl-free-content/
│   ├── SKILL.md          # Agent 工作流定义
│   └── reference.md      # API 规格与分类算法参考
├── scripts/              # 7 个核心爬取脚本
├── data/                 # 运行时 JSON 中间数据（git-ignored）
├── output/               # Excel 报告输出（git-ignored）
├── requirements.txt
└── README.md
```

## 注意事项

- 所有脚本通过 `__file__` 自动定位项目根目录，无需手动配置路径
- 腾讯视频 API 的 `charge=1` 参数不能完全过滤付费内容，`filter_tencent_vip.py` 会进行二次校验
- 优酷爬取依赖浏览器环境（mtop 签名），需要 Browser MCP 支持
- 单平台爬取失败不影响其他平台，Excel 生成时自动跳过缺失数据
