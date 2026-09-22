# CONTEXT.md

本项目的领域词汇表。工程技能在探索代码库、命名 issue 与测试时，应使用本表定义的术语。

## 项目定位

**无印豆包桌面客户端**：从豆包（Doubao）对话分享链接中提取**无水印**图片和视频的 PySide6 桌面应用。

## 平台与域名

- **豆包（Doubao）**：字节跳动 AI 对话产品，域名 `www.doubao.com`。
- **Dola**：豆包的海外版，域名 `www.dola.com`。
- 两者合并称为 **豆包系（Doubao hosts）**。本项目仅支持豆包系，**不支持千问（Qianwen）**。

## 分享链接

- **分享链接（share URL）**：用户在豆包中分享对话后复制的地址，形如 `https://www.doubao.com/thread/<id>`。
- **thread 链接**：必须包含 `/thread/` 路径段，是解析的入口。

## 资源与无水印

- **原图（origin image）**：对话中的无水印原始图片。
- **无水印视频（unwatermarked video）**：去除水印后的视频流。
- **fallback_api**：页面 JSON 中携带的视频接口地址，构造无水印参数后返回视频流地址。
- **视频信息（video info）**：单个视频的元数据（vid、宽高、清晰度、时长、封面、播放地址）。

## 解析

- **解析（parse）**：给定分享链接，返回无水印资源列表的过程。
- **解析包（parser）**：`parser/` 目录，纯逻辑、自包含、零 GUI 依赖。
- **解密（decode）**：将加密/编码的视频 `main_url` token 还原为可直接播放的 HTTP 地址。涉及 **qAAB token**、**AES-CBC**、**Base64**。

## 界面

- **主窗口（main window）**：应用主窗口，含 URL 输入框与「图片 / 视频」两个标签页。
- **素材卡片（asset card）**：展示单个图片或视频的卡片，含查看 / 下载 / 复制操作。
- **后台 worker**：在单独线程执行网络解析与下载，避免阻塞 UI 线程。

## 应避免的同义词

- 用「解析包（parser）」而非「库 / 工具包」。
- 用「豆包系」指代 doubao + dola，而非逐个枚举域名。
- 视频信息中的字段沿用解析包输出的命名（`width`、`height`、`definition`、`poster_url`、`url`）。
