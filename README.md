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
Phase 1.5 腾讯视频 VIP 过滤（mark_label 检测）
Phase 2  优酷列表爬取（需 Browser MCP）
Phase 3  优酷详情补充
Phase 4  四平台汇总 + 性别分类 + Excel 生成
```

## 输出

- 位置：`output/四平台免费内容详情-{YYYYMMDD}.xlsx`
- Sheet1「全部详情」：平台、类型、剧名、年份、演员、地区、集数、题材、男女频
- Sheet2「汇总统计」：各平台电视剧/电影数量及男女频分布
