import os
import json
import time
import logging

# Assuming these modules are now in the same directory or correctly pathed
# from .config import HEADERS # If config.py is in the same 'metadata' package
# from .utils import sanitize_filename, download_image, select_from_results
# from .scrapers.manhuagui_scraper import manhuagui_search_manga, manhuagui_get_manga_details
# from .scrapers.bangumi_scraper import bangumi_search_subject, bangumi_get_subject_details
# from .scrapers.wikipedia_scraper import wikipedia_search_page, wikipedia_get_page_metadata

# For development, if running this file directly, you might need to adjust paths:
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add parent dir (comic_auto_downloader)
from metadata.config import HEADERS
from metadata.utils import sanitize_filename, download_image, select_from_results, get_user_input, get_user_confirmation
from metadata.scrapers.manhuagui_scraper import manhuagui_search_manga, manhuagui_get_manga_details
from metadata.scrapers.bangumi_scraper import bangumi_search_subject, bangumi_get_subject_details
from metadata.scrapers.wikipedia_scraper import wikipedia_search_page, wikipedia_get_page_metadata


logger = logging.getLogger(__name__)

def initialize_manga_directory(base_dir, manga_name_for_dir):
    """Creates the main directory for the manga if it doesn't exist."""
    # Sanitize again to be sure, though the input should be somewhat clean
    safe_manga_name = sanitize_filename(manga_name_for_dir)
    manga_output_dir = os.path.join(base_dir, safe_manga_name)
    if not os.path.exists(manga_output_dir):
        os.makedirs(manga_output_dir)
        logger.info(f"创建目录: {manga_output_dir}")
    return manga_output_dir

def _fetch_and_save_manhuagui_data_internal(chosen_manhuagui_item, manga_output_dir):
    """
    Internal helper to fetch details and cover from Manhuagui and saves them.
    Returns: (manhuagui_metadata_for_file, image_log_entry, chapters_filepath)
    """
    if not chosen_manhuagui_item or not chosen_manhuagui_item.get('url'):
        return {}, None, None

    logger.info("\n--- 正在从 Manhuagui 获取章节和元数据 ---")
    manhuagui_details = manhuagui_get_manga_details(chosen_manhuagui_item['url'])
    manhuagui_metadata_for_file = {}
    image_log_entry = None
    chapters_filepath = None

    if manhuagui_details:
        chapters_data = manhuagui_details.get('chapters_manhuagui', {})
        if chapters_data: # Ensure there are chapters to save
            chapters_filepath = os.path.join(manga_output_dir, "chapters_manhuagui.json")
            with open(chapters_filepath, 'w', encoding='utf-8') as f:
                json.dump(chapters_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Manhuagui 章节列表已保存到: {chapters_filepath}")
        else:
            logger.warning(f"Manhuagui 未能获取到漫画 '{chosen_manhuagui_item['title']}' 的章节列表。")
        
        manhuagui_metadata_for_file = {k: v for k, v in manhuagui_details.items() if k != 'chapters_manhuagui'}
        
        mg_cover_url = manhuagui_details.get('cover_image_url_manhuagui')
        if mg_cover_url and mg_cover_url != 'N/A':
            ext = os.path.splitext(mg_cover_url)[1] or '.jpg'
            mg_cover_filename = f"manhuagui_cover{ext}"
            mg_cover_filepath = os.path.join(manga_output_dir, mg_cover_filename)
            if download_image(mg_cover_url, mg_cover_filepath, "Manhuagui Cover", HEADERS):
                image_log_entry = {'source': 'manhuagui', 'type': 'cover', 'path': mg_cover_filepath, 'url': mg_cover_url}
    else:
        logger.error(f"未能从 Manhuagui 获取 '{chosen_manhuagui_item['title']}' 的详细信息。")
    return manhuagui_metadata_for_file, image_log_entry, chapters_filepath

def _fetch_and_save_bangumi_data_internal(search_term, manga_output_dir):
    logger.info(f"\n--- 正在 Bangumi 搜索 '{search_term}' ---")
    time.sleep(1) # Respect API limits
    bangumi_search_results = bangumi_search_subject(search_term)
    
    chosen_bangumi_item = select_from_results(bangumi_search_results, "Bangumi")
    
    bangumi_metadata_for_file = {}
    image_log_entry = None

    if chosen_bangumi_item and chosen_bangumi_item.get('url'):
        logger.info(f"\n--- 正在从 Bangumi 获取 '{chosen_bangumi_item['title']}' 的元数据 ---")
        time.sleep(1)
        bangumi_details = bangumi_get_subject_details(chosen_bangumi_item['url'])
        if bangumi_details:
            bangumi_metadata_for_file = bangumi_details
            bgm_cover_url = bangumi_details.get('cover_image_url_bangumi')
            if bgm_cover_url and bgm_cover_url != 'N/A':
                ext = os.path.splitext(bgm_cover_url)[1] or '.jpg'
                bgm_cover_filename = f"bangumi_cover{ext}"
                bgm_cover_filepath = os.path.join(manga_output_dir, bgm_cover_filename)
                if download_image(bgm_cover_url, bgm_cover_filepath, "Bangumi Cover", HEADERS):
                    image_log_entry = {'source': 'bangumi', 'type': 'cover', 'path': bgm_cover_filepath, 'url': bgm_cover_url}
        else:
            logger.warning(f"未能从 Bangumi 获取 '{chosen_bangumi_item['title']}' 的详细信息。")
    else:
        logger.info(f"Bangumi 搜索/选择 '{search_term}' 被跳过或失败。")
    return bangumi_metadata_for_file, image_log_entry

def _fetch_and_save_wikipedia_data_internal(search_term, manga_output_dir):
    logger.info(f"\n--- 正在 Wikipedia 搜索 '{search_term}' ---")
    time.sleep(1)
    wikipedia_search_results = wikipedia_search_page(search_term)

    chosen_wikipedia_item = select_from_results(wikipedia_search_results, "Wikipedia")

    wikipedia_metadata_for_file = {}
    image_log_entries = []

    if chosen_wikipedia_item and chosen_wikipedia_item.get('url'):
        logger.info(f"\n--- 正在从 Wikipedia 获取 '{chosen_wikipedia_item['title']}' 的元数据 ---")
        time.sleep(1)
        wiki_metadata = wikipedia_get_page_metadata(chosen_wikipedia_item['url'])
        if wiki_metadata:
            wikipedia_metadata_for_file = wiki_metadata
            wiki_image_urls = wiki_metadata.get('infobox_image_urls_wikipedia', [])
            for idx, img_url in enumerate(wiki_image_urls):
                ext = os.path.splitext(img_url)[1] or '.jpg'
                wiki_img_filename = f"wikipedia_infobox_image_{idx+1}{ext}"
                wiki_img_filepath = os.path.join(manga_output_dir, wiki_img_filename)
                if download_image(img_url, wiki_img_filepath, f"Wikipedia Infobox Image {idx+1}", HEADERS):
                    image_log_entries.append({'source': 'wikipedia', 'type': f'infobox_image_{idx+1}', 'path': wiki_img_filepath, 'url': img_url})
                time.sleep(0.5) # Be gentle
        else:
            logger.warning(f"未能从 Wikipedia 获取 '{chosen_wikipedia_item['title']}' 的元数据。")
    else:
        logger.info(f"Wikipedia 搜索/选择 '{search_term}' 被跳过或失败。")
    return wikipedia_metadata_for_file, image_log_entries

def _save_all_metadata_internal(manga_output_dir, initial_search_term, confirmed_name_for_dir, downloaded_images_log, **kwargs):
    final_metadata = {
        'initial_search_term': initial_search_term,
        'confirmed_name_for_dir': confirmed_name_for_dir,
        'downloaded_images_log': downloaded_images_log
    }
    if kwargs.get('manhuagui_data'):
        final_metadata['manhuagui_data'] = kwargs['manhuagui_data']
    if kwargs.get('bangumi_data'):
        final_metadata['bangumi_data'] = kwargs['bangumi_data']
    if kwargs.get('wikipedia_data'):
        final_metadata['wikipedia_data'] = kwargs['wikipedia_data']
    
    metadata_filepath = os.path.join(manga_output_dir, "metadata.json")
    with open(metadata_filepath, 'w', encoding='utf-8') as f:
        json.dump(final_metadata, f, ensure_ascii=False, indent=4)
    logger.info(f"\n--- 所有元数据已保存到: {metadata_filepath} ---")
    return metadata_filepath

def get_or_fetch_manga_data(initial_manga_name, base_download_dir):
    """
    Checks if manga data exists locally. If not, fetches it with user confirmation.
    Returns a dictionary:
    {
        "success": bool,
        "confirmed_manga_name": str or None, (used for directory)
        "chapters_json_path": str or None,
        "manga_output_dir": str or None
    }
    """
    logger.info(f"开始处理漫画: '{initial_manga_name}'")

    # First, try to find a directory that might match initial_manga_name or its sanitized version
    # This is a simple check; a more robust check might involve reading a manifest if one existed.
    sanitized_initial_name = sanitize_filename(initial_manga_name)
    potential_dir_path = os.path.join(base_download_dir, sanitized_initial_name)
    
    # Check if a directory with the sanitized name and a chapters_manhuagui.json exists
    if os.path.isdir(potential_dir_path):
        chapters_json_path_check = os.path.join(potential_dir_path, "chapters_manhuagui.json")
        if os.path.exists(chapters_json_path_check):
            logger.info(f"在 '{potential_dir_path}' 中找到已存在的漫画数据。")
            # Try to read confirmed name from metadata.json if it exists
            metadata_json_path = os.path.join(potential_dir_path, "metadata.json")
            confirmed_name = sanitized_initial_name # default
            if os.path.exists(metadata_json_path):
                try:
                    with open(metadata_json_path, 'r', encoding='utf-8') as f_meta:
                        meta_content = json.load(f_meta)
                        confirmed_name = meta_content.get('confirmed_name_for_dir', sanitized_initial_name)
                except Exception as e:
                    logger.warning(f"读取现有 metadata.json 失败: {e}")

            return {
                "success": True,
                "confirmed_manga_name": confirmed_name,
                "chapters_json_path": chapters_json_path_check,
                "manga_output_dir": potential_dir_path
            }
        else:
            logger.info(f"找到目录 '{potential_dir_path}' 但缺少 'chapters_manhuagui.json'。将尝试重新获取。")
    else:
        logger.info(f"本地未找到漫画 '{initial_manga_name}' 的数据。开始在线搜索。")

    # --- Online Search and User Confirmation ---
    logger.info("\n--- 正在 Manhuagui 搜索 ---")
    manhuagui_search_results = manhuagui_search_manga(initial_manga_name)

    if not manhuagui_search_results:
        logger.error(f"无法在 Manhuagui 上找到 '{initial_manga_name}'。")
        return {"success": False, "confirmed_manga_name": None, "chapters_json_path": None, "manga_output_dir": None}

    chosen_manhuagui_item = None
    if len(manhuagui_search_results) == 1:
        item = manhuagui_search_results[0]
        # If only one result, check if it's a close enough match or ask for confirmation
        if item['title'].lower() == initial_manga_name.lower():
            logger.info(f"Manhuagui 找到唯一匹配结果: '{item['title']}'，自动选择。")
            chosen_manhuagui_item = item
        else:
            logger.info(f"Manhuagui 找到一个结果: '{item['title']}' (URL: {item['url']})")
            if get_user_confirmation(f"这是您想要的漫画吗? (yes/是/确认)"):
                chosen_manhuagui_item = item
            else:
                logger.info("用户拒绝了该结果。")
                return {"success": False, "confirmed_manga_name": None, "chapters_json_path": None, "manga_output_dir": None}
    else:
        logger.info("Manhuagui 找到多个结果，请选择:")
        chosen_manhuagui_item = select_from_results(manhuagui_search_results, "Manhuagui")

    if not chosen_manhuagui_item:
        logger.error("没有选择 Manhuagui 项目。")
        return {"success": False, "confirmed_manga_name": None, "chapters_json_path": None, "manga_output_dir": None}

    confirmed_manga_name_for_dir = sanitize_filename(chosen_manhuagui_item['title'])
    logger.info(f"已确认 Manhuagui 选择: '{chosen_manhuagui_item['title']}'。将用作目录名: '{confirmed_manga_name_for_dir}'")
    
    manga_output_dir = initialize_manga_directory(base_download_dir, confirmed_manga_name_for_dir)

    all_collected_metadata = {}
    downloaded_images_log = []

    # Manhuagui details and chapters
    mg_meta, mg_img_log, chapters_json_path = _fetch_and_save_manhuagui_data_internal(chosen_manhuagui_item, manga_output_dir)
    if mg_meta: all_collected_metadata['manhuagui_data'] = mg_meta
    if mg_img_log: downloaded_images_log.append(mg_img_log)

    if not chapters_json_path:
        logger.error(f"未能为 '{confirmed_manga_name_for_dir}' 获取 Manhuagui 章节列表。无法继续。")
        # Optionally clean up the created directory if chapters are essential
        # import shutil
        # shutil.rmtree(manga_output_dir)
        # logger.info(f"已删除空目录: {manga_output_dir}")
        return {"success": False, "confirmed_manga_name": confirmed_manga_name_for_dir, "chapters_json_path": None, "manga_output_dir": manga_output_dir}

    # Determine search term for other platforms
    search_term_for_next_steps = chosen_manhuagui_item['title']
    if chosen_manhuagui_item['title'].lower() != initial_manga_name.lower():
        logger.info(f"\n您已从 Manhuagui 选择了: '{chosen_manhuagui_item['title']}'")
        logger.info(f"您最初搜索的词是: '{initial_manga_name}'")
        while True:
            choice = get_user_input("请选择用于后续平台 (Bangumi, Wikipedia) 搜索的标题:\n"
                                     f"1. 使用 Manhuagui 的标题: '{chosen_manhuagui_item['title']}'\n"
                                     f"2. 使用原始输入标题: '{initial_manga_name}'\n"
                                     "请输入选项 (1 或 2): ", valid_inputs=['1', '2'])
            if choice == '1':
                search_term_for_next_steps = chosen_manhuagui_item['title']
                break
            elif choice == '2':
                search_term_for_next_steps = initial_manga_name
                break
        logger.info(f"将使用 '{search_term_for_next_steps}' 进行后续搜索。")
    
    # Bangumi (Optional, can be made configurable)
    bgm_meta, bgm_img_log = _fetch_and_save_bangumi_data_internal(search_term_for_next_steps, manga_output_dir)
    if bgm_meta: all_collected_metadata['bangumi_data'] = bgm_meta
    if bgm_img_log: downloaded_images_log.append(bgm_img_log)
    
    # Wikipedia (Optional, can be made configurable)
    wiki_search_term = search_term_for_next_steps
    if bgm_meta and bgm_meta.get('title_bangumi') and bgm_meta['title_bangumi'].lower() != search_term_for_next_steps.lower():
        logger.info(f"检测到 Bangumi 标题 '{bgm_meta['title_bangumi']}' 与当前搜索词不同。")
        if get_user_confirmation(f"是否使用 Bangumi 标题 '{bgm_meta['title_bangumi']}' 进行 Wikipedia 搜索? (输入 yes/是/确认 使用，其他则使用当前搜索词)"):
            wiki_search_term = bgm_meta['title_bangumi']
            logger.info(f"将使用 '{wiki_search_term}' 进行 Wikipedia 搜索。")
            
    wiki_meta, wiki_img_logs = _fetch_and_save_wikipedia_data_internal(wiki_search_term, manga_output_dir)
    if wiki_meta: all_collected_metadata['wikipedia_data'] = wiki_meta
    if wiki_img_logs: downloaded_images_log.extend(wiki_img_logs)

    _save_all_metadata_internal(manga_output_dir, initial_manga_name, confirmed_manga_name_for_dir, downloaded_images_log, **all_collected_metadata)
    
    logger.info("\n--- 元数据抓取完成! ---")
    logger.info(f"漫画 '{confirmed_manga_name_for_dir}' 的数据保存在目录: {manga_output_dir}")
    if downloaded_images_log:
        logger.info("已下载图片:")
        for img_log in downloaded_images_log:
            logger.info(f"  - 来源: {img_log['source']}, 类型: {img_log['type']}, 路径: {img_log['path']}")
    
    logger.info(f"Manhuagui 章节列表位于: {chapters_json_path}")

    return {
        "success": True,
        "confirmed_manga_name": confirmed_manga_name_for_dir,
        "chapters_json_path": chapters_json_path,
        "manga_output_dir": manga_output_dir
    }

if __name__ == '__main__':
    # Example usage:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Create a dummy base_download_dir for testing
    test_base_dir = "test_downloaded_comics"
    if not os.path.exists(test_base_dir):
        os.makedirs(test_base_dir)

    # manga_to_test = "一人之下"
    manga_to_test = get_user_input("请输入要测试的漫画名称: ")
    
    # Clean up previous test run for this manga if it exists
    # test_manga_sanitized_name = sanitize_filename(manga_to_test) # This might not be the final dir name
    # potential_test_manga_dir = os.path.join(test_base_dir, test_manga_sanitized_name)
    # if os.path.exists(potential_test_manga_dir):
    #     import shutil
    #     logger.info(f"Cleaning up previous test directory: {potential_test_manga_dir}")
    #     shutil.rmtree(potential_test_manga_dir)
        
    result = get_or_fetch_manga_data(manga_to_test, test_base_dir)
    
    if result["success"]:
        logger.info(f"\n测试成功完成!")
        logger.info(f"确认的漫画名称: {result['confirmed_manga_name']}")
        logger.info(f"章节JSON路径: {result['chapters_json_path']}")
        logger.info(f"输出目录: {result['manga_output_dir']}")
    else:
        logger.error(f"\n测试失败。")

    # To fully test, you'd then pass result['chapters_json_path'] to the chapter downloader.