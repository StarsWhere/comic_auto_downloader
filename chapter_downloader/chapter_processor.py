import json
import os
import time
import logging
import re
import glob # For finding image files
from PIL import Image # For PDF creation

# Adjust import for the new structure
# from .screenshot_engine import capture_chapter_images, target_image_id, blocked_urls, vertical_offset
# For development, if running this file directly, you might need to adjust paths:
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add parent dir (comic_auto_downloader)
from chapter_downloader.screenshot_engine import capture_chapter_images, target_image_id, blocked_urls, vertical_offset


logger = logging.getLogger(__name__)

def sanitize_filename_for_path(filename):
    """Cleans filename for use in paths, removing or replacing invalid characters."""
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # Remove basic invalid characters
    filename = re.sub(r'\s+', '_', filename) # Replace spaces with underscores
    return filename

def get_chapter_sort_key(title):
    """
    Extracts a sortable key (float) from chapter titles.
    Handles "第X话", "第X卷", "番外篇X", and general "番外篇".
    """
    # Case 1: "第X话" or "第X卷" (X can be int or float)
    match_vol_chap = re.search(r'第(\d+(\.\d+)?)(话|卷)', title)
    if match_vol_chap:
        return (0, float(match_vol_chap.group(1))) # Sort by type (0 for main), then number

    # Case 2: "番外篇X" (X is an integer)
    match_extra_num = re.search(r'番外篇(\d+)', title)
    if match_extra_num:
        return (1, int(match_extra_num.group(1))) # Sort by type (1 for numbered extra), then number
    
    # Case 3: Generic "番外篇" (without a number following directly)
    if "番外篇" in title:
        # Try to find any number in the title for secondary sort, otherwise use a fixed high number
        match_any_num_in_extra = re.search(r'(\d+)', title)
        if match_any_num_in_extra:
            return (2, int(match_any_num_in_extra.group(1))) # Sort by type (2 for generic extra), then any found number
        return (2, float('inf') - 100) # Generic extras sorted after numbered ones

    # Case 4: No discernible chapter/volume/extra number, try to find any number
    match_any_num = re.search(r'(\d+)', title)
    if match_any_num:
        return (3, int(match_any_num.group(1))) # Sort by type (3 for other numbered), then number

    # Case 5: No numbers at all, sort by title alphabetically as a last resort
    return (4, title.lower())

def create_pdf_from_chapter_images(chapter_images_dir, output_pdf_path):
    """
    Creates a PDF file from all .png images in a given directory.
    Images are sorted numerically by their filenames (e.g., 1.png, 2.png, ...).
    """
    logger.info(f"开始为目录 '{chapter_images_dir}' 创建 PDF 到 '{output_pdf_path}'")
    try:
        image_paths = sorted(
            glob.glob(os.path.join(chapter_images_dir, '*.png')),
            key=lambda x: int(os.path.splitext(os.path.basename(x))[0]) # Sort by page number
        )

        if not image_paths:
            logger.warning(f"在目录 '{chapter_images_dir}' 中未找到 PNG 图片，无法创建 PDF。")
            return False

        images_pil = []
        first_image = None
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                # Convert to RGB to avoid issues with different image modes (e.g., RGBA, P)
                # and to ensure compatibility for saving as PDF.
                if img.mode == 'RGBA' or img.mode == 'P':
                    img = img.convert('RGB')
                elif img.mode != 'RGB': # Handle other modes like L (grayscale) etc.
                    logger.info(f"图片 '{img_path}' 模式为 {img.mode}, 转换为 RGB。")
                    img = img.convert('RGB')

                if first_image is None:
                    first_image = img
                else:
                    images_pil.append(img)
            except Exception as e:
                logger.error(f"打开或转换图片 '{img_path}' 失败: {e}")
                return False # Fail PDF creation if one image fails

        if first_image is None: # Should be caught by the earlier check if image_paths is empty
            logger.warning(f"没有可用于创建 PDF 的有效图片。")
            return False

        first_image.save(
            output_pdf_path,
            save_all=True,
            append_images=images_pil, # Pass the list of subsequent images
            resolution=100.0 # Optional: set resolution
        )
        logger.info(f"PDF 已成功创建并保存到: {output_pdf_path}")
        return True
    except Exception as e:
        logger.error(f"创建 PDF '{output_pdf_path}' 失败: {e}", exc_info=True)
        return False

def download_chapters_from_json_file(json_file_path):
    """
    Processes the JSON file and downloads manga chapters.
    Returns True if all operations completed (even if some chapters failed individual downloads),
    False if there was a critical error like file not found or JSON parsing error.
    """
    if not os.path.exists(json_file_path):
        logger.error(f"JSON 文件未找到: {json_file_path}")
        return False

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"读取或解析JSON文件失败: {json_file_path} - {e}")
        return False

    base_manga_dir = os.path.dirname(json_file_path)
    logger.info(f"漫画根目录: {base_manga_dir}")

    # Define processing order for chapter types if they exist as keys in the JSON
    # User-defined order: "番外篇", "单行本", "单话"
    preferred_order = ["番外篇", "单行本", "单话"]
    
    # Get all types present in the JSON data
    available_types = list(data.keys())
    
    # Order the types: first the preferred ones that are available, then any other available types
    ordered_chapter_types_to_process = []
    
    # Add preferred types if they exist
    for p_type in preferred_order:
        if p_type in available_types:
            ordered_chapter_types_to_process.append(p_type)
            available_types.remove(p_type) # Remove to avoid processing twice
            
    # Add any remaining types (those not in preferred_order but present in JSON)
    ordered_chapter_types_to_process.extend(available_types)

    if not ordered_chapter_types_to_process:
        logger.info("JSON文件中没有找到可处理的章节类型。")
        return True # No chapters to process is not an error in itself

    all_chapters_processed_successfully = True # Track overall success

    for chapter_type in ordered_chapter_types_to_process:
        if not isinstance(data.get(chapter_type), list):
            logger.warning(f"在JSON文件中，'{chapter_type}' 的值不是列表，跳过。")
            continue
            
        chapters_to_process = data[chapter_type]
        if not chapters_to_process:
            logger.info(f"章节类型 '{chapter_type}' 为空，跳过。")
            continue
        
        # Sort chapters using the new sort key function
        chapters_to_process.sort(key=lambda x: get_chapter_sort_key(x.get("title", "")))
        logger.info(f"开始处理类型 '{chapter_type}'，共 {len(chapters_to_process)} 章 (已排序)。")

        for chapter_info in chapters_to_process:
            title = chapter_info.get("title")
            url = chapter_info.get("url")
            completed = chapter_info.get("completed", False)

            if not title or not url:
                logger.warning(f"章节信息不完整，跳过: {chapter_info}")
                continue

            if completed:
                logger.info(f"章节 '{title}' 已标记为完成，跳过。")
                continue

            sanitized_title_for_dir = sanitize_filename_for_path(title)
            sanitized_chapter_type_for_dir = sanitize_filename_for_path(chapter_type)
            
            chapter_output_full_dir = os.path.join(base_manga_dir, sanitized_chapter_type_for_dir, sanitized_title_for_dir)
            os.makedirs(chapter_output_full_dir, exist_ok=True)
            logger.info(f"创建/确认目录: {chapter_output_full_dir}")

            logger.info(f"开始下载章节: '{title}' (URL: {url})")
            
            download_successful_for_chapter = False
            attempts = 0
            max_attempts = 3

            while attempts < max_attempts and not download_successful_for_chapter:
                attempts += 1
                logger.info(f"尝试第 {attempts}/{max_attempts} 次下载章节 '{title}'")
                try:
                    capture_successful_flag = capture_chapter_images(
                        start_url=url,
                        image_id=target_image_id, # These should be imported from screenshot_engine
                        urls_to_block=blocked_urls,
                        vertical_offset_compensation=vertical_offset,
                        base_output_dir=chapter_output_full_dir
                    )
                    if capture_successful_flag: # Assuming capture_chapter_images returns True on success
                        download_successful_for_chapter = True
                        logger.info(f"章节 '{title}' 下载成功。")
                    else:
                        logger.warning(f"章节 '{title}' 第 {attempts} 次下载失败 (截图引擎报告失败)。")
                except Exception as e:
                    logger.error(f"下载章节 '{title}' (尝试 {attempts}) 时发生错误: {e}", exc_info=True)
                
                if not download_successful_for_chapter and attempts < max_attempts:
                    logger.info(f"等待5秒后重试...")
                    time.sleep(5)

            if download_successful_for_chapter:
                # PDF Creation Step
                # PDF will be saved in the chapter type directory, e.g., downloaded_comics/MangaName/ChapterType/ChapterTitle.pdf
                pdf_filename = f"{sanitized_title_for_dir}.pdf"
                # chapter_output_full_dir is like downloaded_comics/MangaName/ChapterType/ChapterTitle_img_folder
                # So, os.path.dirname(chapter_output_full_dir) gives downloaded_comics/MangaName/ChapterType/
                pdf_output_path = os.path.join(os.path.dirname(chapter_output_full_dir), pdf_filename)

                logger.info(f"尝试为章节 '{title}' 从 '{chapter_output_full_dir}' 创建 PDF 文件到 '{pdf_output_path}'...")
                pdf_created_successfully = create_pdf_from_chapter_images(chapter_output_full_dir, pdf_output_path)

                if pdf_created_successfully:
                    logger.info(f"章节 '{title}' 的 PDF 创建成功。")
                    chapter_info["completed"] = True # Mark completed only if PDF is also created
                    try:
                        with open(json_file_path, 'w', encoding='utf-8') as f_update:
                            json.dump(data, f_update, ensure_ascii=False, indent=4)
                        logger.info(f"已更新JSON文件，标记章节 '{title}' 为已完成。")
                    except Exception as e:
                        logger.error(f"更新JSON文件失败: {e}")
                        all_chapters_processed_successfully = False # If JSON update fails, it's an issue
                    
                    logger.info(f"章节 '{title}' (包括PDF) 处理完毕，暂停5秒...")
                    time.sleep(5) # Be kind to servers
                else:
                    logger.error(f"章节 '{title}' 的 PDF 创建失败。章节将不会被标记为已完成。")
                    all_chapters_processed_successfully = False # Mark that at least one chapter (PDF part) failed
            else:
                logger.error(f"章节 '{title}' 下载失败 {max_attempts} 次，跳过此章节。")
                all_chapters_processed_successfully = False # Mark that at least one chapter failed

    logger.info("所有章节类型处理完毕。")
    return all_chapters_processed_successfully


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Example usage:
    # Create a dummy JSON file for testing
    dummy_manga_name = "测试漫画"
    dummy_base_dir = os.path.join("..", "downloaded_comics") # Assuming this script is in chapter_downloader
    dummy_manga_dir = os.path.join(dummy_base_dir, dummy_manga_name)
    os.makedirs(dummy_manga_dir, exist_ok=True)
    
    dummy_json_path = os.path.join(dummy_manga_dir, "chapters_manhuagui.json")
    
    test_data = {
        "单话": [
            {"title": "第1话", "url": "http://example.com/chap1", "completed": False},
            {"title": "第2话", "url": "http://example.com/chap2", "completed": True},
            {"title": "第0.5话", "url": "http://example.com/chap0.5", "completed": False},
            {"title": "番外篇1", "url": "http://example.com/extra1", "completed": False}
        ],
        "番外篇": [
             {"title": "特别篇", "url": "http://example.com/special", "completed": False}
        ]
    }
    # Create a dummy screenshot_engine.py in the same directory for this test to run
    # with open("screenshot_engine.py", "w") as f_engine:
    #     f_engine.write(
    #         "target_image_id = 'comicImg'\n"
    #         "blocked_urls = []\n"
    #         "vertical_offset = 0\n"
    #         "def capture_chapter_images(start_url, image_id, urls_to_block, vertical_offset_compensation, base_output_dir):\n"
    #         "    print(f'SIMULATE: Capturing {start_url} to {base_output_dir}')\n"
    #         "    # Simulate creating some image files\n"
    #         "    os.makedirs(base_output_dir, exist_ok=True)\n"
    #         "    with open(os.path.join(base_output_dir, 'page1.png'), 'w') as f: f.write('dummy')\n"
    #         "    return True\n"
    #     )


    if not os.path.exists(dummy_json_path) or True: # Force create for testing
        with open(dummy_json_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=4)
        logger.info(f"创建测试JSON文件: {dummy_json_path}")

    logger.info("开始测试章节下载器...")
    success = download_chapters_from_json_file(dummy_json_path)
    if success:
        logger.info("章节下载器测试（模拟）完成。检查输出和JSON文件。")
    else:
        logger.error("章节下载器测试遇到问题。")
    
    # Clean up dummy screenshot_engine.py if created
    # if os.path.exists("screenshot_engine.py"):
    #     os.remove("screenshot_engine.py")