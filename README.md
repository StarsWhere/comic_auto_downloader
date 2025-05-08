# Comic Auto Downloader

Comic Auto Downloader 是一个 Python 脚本，旨在自动化搜索、获取元数据和下载漫画章节的过程。它首先会检查本地是否存在漫画数据，如果不存在，则会从网络上获取元数据（如 Manhuagui、Bangumi、Wikipedia）并提示用户确认，然后下载漫画章节。对于已存在的漫画，它会直接开始下载未完成的章节。

## 主要功能

*   **智能漫画搜索与元数据获取：**
    *   用户提供漫画名称进行搜索。
    *   自动从 Manhuagui 等平台搜索漫画。
    *   如果搜索结果不唯一或与输入不完全匹配，会提示用户进行选择和确认。
    *   获取并保存漫画的详细元数据，包括标题、封面、作者、简介等。
    *   支持从多个来源（Manhuagui、Bangumi、Wikipedia）聚合元数据。
*   **本地数据优先：**
    *   在进行网络搜索前，首先检查本地 `downloaded_comics` 目录中是否已存在该漫画的数据。
    *   如果找到有效的本地数据（包含 `chapters_manhuagui.json`），则跳过元数据获取步骤。
*   **章节智能下载与管理：**
    *   基于 `chapters_manhuagui.json` 文件管理章节下载。
    *   自动跳过已标记为 `completed: true` 的章节。
    *   下载完成后，自动将章节标记为 `completed: true`。
    *   章节图片会保存到以漫画名和章节名组织的目录结构中。
    *   支持下载重试机制。
*   **清晰的目录结构：**
    *   所有下载的漫画都存储在 `downloaded_comics` 基础目录下。
    *   每个漫画有其独立的子目录，包含元数据文件 (`metadata.json`)、章节列表 (`chapters_manhuagui.json`) 和封面图片。
    *   每个章节的图片存储在其对应的子目录中。
*   **日志记录：**
    *   详细记录程序运行过程中的信息、警告和错误，方便追踪和调试。

## 项目结构

```
comic_auto_downloader/
├── main.py                     # 主程序入口
├── chapter_downloader/         # 章节下载模块
│   ├── __init__.py
│   ├── chapter_processor.py    # 处理章节下载逻辑，读取JSON，调用截图引擎
│   └── screenshot_engine.py    # 负责实际的网页截图和图片保存 (依赖 Playwright)
├── metadata/                   # 元数据获取模块
│   ├── __init__.py
│   ├── config.py               # 配置文件 (例如请求头)
│   ├── metadata_fetcher.py     # 获取元数据的主逻辑，处理本地检查和网络抓取
│   ├── utils.py                # 工具函数 (例如文件名清理、图片下载)
│   └── scrapers/               # 各个网站的爬虫实现
│       ├── __init__.py
│       ├── bangumi_scraper.py
│       ├── manhuagui_scraper.py
│       └── wikipedia_scraper.py
├── downloaded_comics/          # (程序运行时自动创建) 存储下载的漫画和元数据
│   └── [漫画名称]/
│       ├── metadata.json
│       ├── chapters_manhuagui.json
│       ├── manhuagui_cover.jpg
│       ├── bangumi_cover.jpg
│       └── [章节类型]/
│           └── [章节标题]/
│               └── page_1.png
│               └── ...
└── README.md                   # 本文档
```

## 环境准备

1.  **Python:** 确保您已安装 Python 3.7 或更高版本。
2.  **pip:** Python 包管理工具，通常随 Python 一起安装。
3.  **Selenium WebDriver 和 WebDriver Manager:** `screenshot_engine.py` 使用 Selenium 进行网页截图，并使用 WebDriver Manager 自动管理浏览器驱动（例如 ChromeDriver）。

## 安装指南

1.  **克隆仓库 (如果您从 Git 获取):**
    ```bash
    git clone <repository_url>
    cd comic_auto_downloader
    ```
    如果您已拥有文件，请直接进入项目根目录 `comic_auto_downloader`。

2.  **创建并激活虚拟环境 (推荐):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **安装 Python 依赖包:**
    项目依赖以下 Python 包。您可以通过 `pip` 安装它们：
    ```bash
    pip install requests beautifulsoup4 selenium webdriver-manager Pillow
    ```
    *   `requests`: 用于发送 HTTP 请求。
    *   `beautifulsoup4`: 用于解析 HTML 内容。
    *   `selenium`: 用于浏览器自动化和网页截图。
    *   `webdriver-manager`: 用于自动管理 Selenium WebDriver 的浏览器驱动（如 ChromeDriver）。
    *   `Pillow`: 用于图像处理（例如截图后的裁剪）。

4.  **浏览器驱动:**
    `webdriver-manager` 会在首次运行时自动下载并配置合适的 ChromeDriver。您通常不需要手动安装浏览器驱动。确保您的系统上安装了 Google Chrome 浏览器。

## 使用方法

1.  确保您已按照上述步骤完成安装和环境配置。
2.  打开终端或命令行，导航到 `comic_auto_downloader` 项目的根目录。
3.  运行主程序：
    ```bash
    python main.py
    ```
4.  程序会提示您输入要搜索和下载的漫画名称：
    ```
    请输入要搜索和下载的漫画名称: [在此输入漫画名]
    ```
5.  根据提示进行操作：
    *   如果找到多个匹配项或匹配项不精确，程序会列出选项供您选择或确认。
    *   程序会自动处理元数据获取和章节下载。
6.  下载的漫画将保存在项目根目录下的 `downloaded_comics` 文件夹中。日志信息会直接输出到控制台。

## 工作流程详解

1.  **启动与输入:**
    *   用户运行 `main.py` 并输入目标漫画的名称。

2.  **元数据处理 (`metadata_fetcher.py`):**
    *   **本地检查:** 程序首先根据用户输入的漫画名（经过初步清理）在 `downloaded_comics` 目录下查找是否已存在对应的漫画文件夹，并且该文件夹内是否包含 `chapters_manhuagui.json` 文件。
    *   **命中本地数据:** 如果找到有效的本地数据，则直接使用该数据，跳过在线搜索步骤。程序会从本地 `metadata.json` (如果存在) 读取确认的漫画名称。
    *   **在线搜索 (Manhuagui):** 如果本地没有数据或数据不完整，程序会使用 `manhuagui_scraper.py` 在 Manhuagui 网站上搜索漫画。
    *   **用户确认/选择:**
        *   如果只有一个搜索结果且与输入名称精确匹配（忽略大小写），则自动选择。
        *   如果只有一个结果但不完全匹配，或有多个结果，程序会列出这些结果，并要求用户确认或选择正确的漫画。
        *   如果用户未选择或拒绝所有结果，程序将终止该漫画的处理。
    *   **获取详细元数据:** 一旦用户确认了 Manhuagui 上的漫画条目：
        *   程序会从 Manhuagui 获取该漫画的详细信息，包括封面图片URL、章节列表等，并保存 `chapters_manhuagui.json`。
        *   用户会被询问希望使用哪个标题（原始输入或 Manhuagui 确认的标题）去搜索其他平台（Bangumi, Wikipedia）。
    *   **多平台元数据聚合 (Bangumi, Wikipedia):**
        *   程序会使用选定的搜索词，通过 `bangumi_scraper.py` 和 `wikipedia_scraper.py` 分别从 Bangumi 和 Wikipedia 获取补充元数据和封面/信息框图片。
        *   这些平台的搜索结果也会进行用户选择（如果需要）。
    *   **保存元数据:** 所有收集到的元数据（包括各平台信息、下载的图片记录）会被整合并保存到该漫画目录下的 `metadata.json` 文件中。封面图片也会被下载到漫画目录。

3.  **章节下载处理 (`chapter_processor.py`):**
    *   `main.py` 将获取到的 `chapters_manhuagui.json` 文件路径传递给章节处理器。
    *   **读取章节列表:** 处理器读取 JSON 文件，获取所有章节类型（如“单话”、“番外篇”）及其下的章节列表。
    *   **章节排序:** 章节会根据其标题中的数字（如“第X话”）进行排序，以确保下载顺序基本正确。
    *   **检查完成状态:** 对于每个章节，程序会检查其 `completed` 字段。
        *   如果 `completed` 为 `true`，则跳过该章节。
    *   **创建章节目录:** 为未完成的章节创建输出目录，路径通常是 `downloaded_comics/[漫画名]/[章节类型]/[章节标题]/`。
    *   **调用截图引擎 (`screenshot_engine.py`):**
        *   对于需要下载的章节，程序调用 `capture_chapter_images` 函数。
        *   此函数使用 Selenium 和 WebDriver Manager 启动一个无头 Chrome 浏览器，访问章节的 URL。
        *   它会模拟滚动页面、定位漫画图片元素、并逐页截图，直到所有图片被捕获。
        *   截图会保存到之前创建的章节目录中。
    *   **更新完成状态:** 章节所有图片下载（截图）成功后，`chapter_processor.py` 会更新内存中的章节数据，将该章节的 `completed` 标记为 `true`，然后将整个更新后的章节列表写回 `chapters_manhuagui.json` 文件。
    *   **下载间隔与重试:**
        *   每成功下载一个章节后，程序会暂停一小段时间（例如5秒），以避免对服务器造成过大压力。
        *   如果单章节下载失败，会进行有限次数的重试。

4.  **完成:**
    *   所有章节处理完毕后，`main.py` 会输出总结信息。

## 注意事项

*   **网络依赖:** 本程序高度依赖网络连接以及目标网站（Manhuagui, Bangumi, Wikipedia）的可用性和页面结构。如果网站结构发生变化，爬虫部分可能需要更新。
*   **Selenium 和 ChromeDriver:** `webdriver-manager` 会尝试自动管理 ChromeDriver。如果遇到驱动问题，请确保您的 Google Chrome 浏览器是最新版本，或者检查 `webdriver-manager` 的相关文档。
*   **IP 限制/反爬机制:** 频繁访问某些网站可能会触发反爬机制。程序中已包含一些基本的延时，但如果遇到问题，可能需要调整延时或使用代理。
*   **法律与版权:** 请尊重漫画的版权。本工具仅供学习和个人便利使用，请勿用于非法传播或商业用途。

## 未来可能的改进

*   增加图形用户界面 (GUI)。
*   支持更多漫画网站源。
*   更高级的错误处理和恢复机制。
*   支持代理配置。
*   将下载的图片合成为 PDF 或 CBZ/CBR 文件。
*   更灵活的配置选项（例如通过配置文件设置下载延时、重试次数等）。