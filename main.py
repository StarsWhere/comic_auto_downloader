import os
import json
import shutil # For copying utility if needed, though direct function calls are better
import logging
import argparse

# Assuming the new structure:
# comic_auto_downloader/
# ├── metadata/
# │   ├── metadata_fetcher.py
# ...
# ├── chapter_downloader/
# │   ├── chapter_processor.py
# ...
# └── main.py

# Adjust import paths based on the new structure
# We'll need to define how metadata_fetcher and chapter_processor are called.
# For now, let's assume they have main functions we can import and call.
from metadata.metadata_fetcher import get_or_fetch_manga_data
from chapter_downloader.chapter_processor import download_chapters_from_json_file


BASE_DOWNLOAD_DIR = "downloaded_comics"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def sanitize_filename_for_dir(filename):
    """Basic sanitization for directory names."""
    return "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in filename).rstrip()

def run_downloader():
    from metadata.utils import get_user_input
    manga_name_input = get_user_input("请输入要搜索和下载的漫画名称: ")
    if not manga_name_input:
        logger.error("漫画名称不能为空。")
        return

    # Sanitize the input manga name to create a potential directory name
    # The actual directory name will be confirmed by the metadata fetcher
    potential_manga_dir_name = sanitize_filename_for_dir(manga_name_input)
    
    # The metadata fetcher will determine the final confirmed manga name and directory.
    # It will also handle the logic of asking for confirmation if matches are not accurate.
    
    # Call the metadata fetcher
    manga_data_result = get_or_fetch_manga_data(manga_name_input, BASE_DOWNLOAD_DIR)

    if not manga_data_result or not manga_data_result.get("success"):
        logger.error(f"未能为漫画 '{manga_name_input}' 获取元数据。程序终止。")
        return

    chapters_json_path = manga_data_result.get("chapters_json_path")
    confirmed_manga_name = manga_data_result.get("confirmed_manga_name")

    if not chapters_json_path:
        logger.error(f"元数据处理成功，但未找到章节JSON文件路径 for '{confirmed_manga_name}'。无法下载章节。")
        return

    logger.info(f"漫画 '{confirmed_manga_name}' 的元数据已准备就绪。章节列表位于: {chapters_json_path}")
    logger.info(f"开始下载漫画 '{confirmed_manga_name}' 的章节...")

    # Call the chapter downloader
    download_overall_success = download_chapters_from_json_file(chapters_json_path)

    if download_overall_success:
        logger.info(f"漫画 '{confirmed_manga_name}' 的所有章节已处理。请检查日志了解详情。")
    else:
        logger.warning(f"漫画 '{confirmed_manga_name}' 的章节下载过程中遇到一些问题。请检查日志。")

    logger.info(f"漫画 '{manga_name_input}' (确认为: '{confirmed_manga_name}') 的处理流程结束。")


if __name__ == "__main__":
    # Create base download directory if it doesn't exist
    if not os.path.exists(BASE_DOWNLOAD_DIR):
        os.makedirs(BASE_DOWNLOAD_DIR)
        logger.info(f"创建基础下载目录: {BASE_DOWNLOAD_DIR}")
    
    run_downloader()