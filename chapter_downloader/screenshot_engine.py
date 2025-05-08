from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
from PIL import Image
import time
import os
import re # 用于从URL提取数字
import logging
import io # 用于 BytesIO

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def isolate_element_js(driver, element_id):
    script = """
        var targetElement = document.getElementById(arguments[0]);
        if (!targetElement) {
            console.error('目标元素 ' + arguments[0] + ' 在隔离时未找到。');
            return false;
        }
        var bodyChildren = document.body.children;
        for (var i = 0; i < bodyChildren.length; i++) {
            bodyChildren[i].style.setProperty('display', 'none', 'important');
        }
        var current = targetElement;
        var pathElements = [];
        while (current && current !== document.body) {
            pathElements.push(current);
            current = current.parentElement;
        }
        pathElements.forEach(function(el) {
            el.style.setProperty('display', '', '');
            el.style.setProperty('visibility', 'visible', 'important');
            if (el.parentElement) {
                 el.parentElement.style.overflow = 'visible';
            }
        });
        document.body.style.setProperty('display', '', '');
        document.body.style.setProperty('visibility', 'visible', 'important');
        document.body.style.overflow = 'visible';
        if (document.documentElement) {
            document.documentElement.style.setProperty('display', '', '');
            document.documentElement.style.setProperty('visibility', 'visible', 'important');
            document.documentElement.style.overflow = 'visible';
        }
        targetElement.scrollIntoView({block: 'center', inline: 'center'});
        return true;
    """
    try:
        success = driver.execute_script(script, element_id)
        if success:
            logger.info(f"已尝试通过JavaScript隔离元素 '{element_id}' 并将其滚动到视图中。")
        else:
            logger.warning(f"JavaScript隔离元素 '{element_id}' 失败：脚本返回false。")
        return success
    except Exception as e:
        logger.error(f"执行JavaScript隔离元素 '{element_id}' 时出错: {e}", exc_info=True)
        return False

def capture_single_page_image(
    driver,
    wait,
    image_id,
    vertical_offset_compensation,
    output_dir,
    page_number
):
    try:
        logger.info(f"第 {page_number} 页：等待图片元素 '{image_id}' 存在且可见。")
        image_element = wait.until(EC.visibility_of_element_located((By.ID, image_id)))
        
        if not isolate_element_js(driver, image_id):
            logger.warning(f"第 {page_number} 页：JS隔离失败。尝试手动滚动。")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", image_element)
            time.sleep(0.5)
        else:
            time.sleep(1.5) 

        logger.info(f"第 {page_number} 页：等待图片完全加载 (complete, naturalWidth > 0, clientRects存在)。")
        try:
            wait.until(lambda d: d.execute_script(
                "return arguments[0].complete && typeof arguments[0].naturalWidth != 'undefined' && arguments[0].naturalWidth > 0 && arguments[0].getClientRects().length > 0",
                image_element
            ))
            logger.info(f"第 {page_number} 页：图片已完全加载。")
        except TimeoutException:
            logger.warning(f"第 {page_number} 页：等待图片加载超时。截图可能不完整。")
        
        try:
            image_element = driver.find_element(By.ID, image_id)
            location_css = image_element.location
            size_css = image_element.size
            logger.info(f"第 {page_number} 页：图片CSS位置: {location_css}, 尺寸: {size_css}")
        except NoSuchElementException:
            logger.error(f"第 {page_number} 页：在获取最终位置前，图片元素 '{image_id}' 消失。")
            return False

        if not size_css or size_css['width'] == 0 or size_css['height'] == 0:
            logger.error(f"第 {page_number} 页：无效的图片尺寸: {size_css}。跳过此页。")
            return False

        doc_scroll_height = driver.execute_script("return document.documentElement.scrollHeight;")
        doc_scroll_width = driver.execute_script("return document.documentElement.scrollWidth;")
        element_bottom_css = location_css['y'] + size_css['height']
        
        page_height_to_set = max(doc_scroll_height, element_bottom_css + 200, 3000)
        initial_window_width = driver.get_window_size().get('width', 1920)
        page_width_to_set = max(doc_scroll_width, initial_window_width, location_css['x'] + size_css['width'] + 100)

        current_window_size = driver.get_window_size()
        if current_window_size['width'] != page_width_to_set or current_window_size['height'] != page_height_to_set:
            logger.info(f"第 {page_number} 页：调整窗口大小为 {page_width_to_set}x{page_height_to_set}")
            driver.set_window_size(page_width_to_set, page_height_to_set)
            time.sleep(2)
        
        final_cropped_path = os.path.join(output_dir, f"{page_number}.png")

        image_element = driver.find_element(By.ID, image_id)
        location_css = image_element.location
        size_css = image_element.size

        dpr_script_output = driver.execute_script('return window.devicePixelRatio')
        dpr = float(dpr_script_output) if dpr_script_output else 1.0
        logger.info(f"第 {page_number} 页：设备像素比 (DPR): {dpr}")

        logger.info(f"第 {page_number} 页：正在进行截图。")
        screenshot_bytes = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot_bytes))
        logger.info(f"第 {page_number} 页：完整截图尺寸 (物理像素): {img.width}x{img.height}")

        compensated_top_css = location_css['y'] - vertical_offset_compensation
        left_phys = int(location_css['x'] * dpr)
        top_phys = int(compensated_top_css * dpr)
        right_phys = int((location_css['x'] + size_css['width']) * dpr)
        bottom_phys = int((compensated_top_css + size_css['height']) * dpr)

        crop_left = max(0, left_phys)
        crop_top = max(0, top_phys)
        crop_right = min(img.width, right_phys)
        crop_bottom = min(img.height, bottom_phys)

        if crop_left >= crop_right or crop_top >= crop_bottom:
            logger.error(f"第 {page_number} 页：无效的裁剪区域: 左{crop_left} 上{crop_top} 右{crop_right} 下{crop_bottom}。跳过裁剪。")
            return False

        logger.info(f"第 {page_number} 页：裁剪区域: 左{crop_left} 上{crop_top} 右{crop_right} 下{crop_bottom}")
        cropped_img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
        cropped_img.save(final_cropped_path)
        logger.info(f"第 {page_number} 页：已保存裁剪后的图片到 {final_cropped_path}")
        return True

    except NoSuchElementException:
        logger.error(f"第 {page_number} 页：图片元素 '{image_id}' 未找到。", exc_info=True)
        return False
    except TimeoutException:
        logger.error(f"第 {page_number} 页：图片捕获过程中超时。", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"第 {page_number} 页：捕获图片时发生错误: {e}", exc_info=True)
        return False

def click_next_page_button(driver, wait, image_id_to_staleness_check):
    next_page_button = None
    try:
        next_page_buttons = driver.find_elements(By.XPATH, "//div[@id='pagination']//a[contains(@class, 'next') and (contains(text(), '下一页') or contains(@href, 'SMH.utils.goPage'))]")
        for btn in next_page_buttons:
            onclick_value = btn.get_attribute("onclick")
            is_next_chapter_button = False
            if onclick_value and "nextC" in onclick_value:
                is_next_chapter_button = True
            if "下一章" not in btn.text and not is_next_chapter_button:
                next_page_button = btn
                break
        
        if not next_page_button:
            logger.info("未找到“下一页”按钮（不是 'a' 标签或不符合条件）。假定已到章节末尾。")
            return False

        # 主 try 块，用于处理点击和导航操作
        logger.info("正在将“下一页”按钮滚动到视图中。")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", next_page_button)
        time.sleep(0.2) 

        old_image_element = driver.find_element(By.ID, image_id_to_staleness_check)

        if not next_page_button.is_displayed():
            logger.warning("“下一页”按钮找到但在滚动后未显示。尝试使用 JavaScript 点击作为后备。")
            driver.execute_script("arguments[0].click();", next_page_button)
        else:
            logger.info("“下一页”按钮已显示。等待其变为可点击状态并尝试点击。")
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(next_page_button))
                next_page_button.click()
            except ElementClickInterceptedException:
                logger.warning("点击“下一页”按钮时发生 ElementClickInterceptedException，尝试使用 JavaScript 点击。")
                driver.execute_script("arguments[0].click();", next_page_button)
            except TimeoutException: 
                logger.warning("等待“下一页”按钮变为可点击状态超时，尝试使用 JavaScript 点击。")
                driver.execute_script("arguments[0].click();", next_page_button)
        
        logger.info("等待页面导航（旧图片元素变为陈旧状态）...")
        wait.until(EC.staleness_of(old_image_element))
        
        logger.info(f"等待新图片 '{image_id_to_staleness_check}' 在导航后可见...")
        wait.until(EC.visibility_of_element_located((By.ID, image_id_to_staleness_check)))
        
        logger.info("成功导航到下一页。")
        time.sleep(0.5) 
        return True

    except NoSuchElementException as nse: 
        logger.error(f"在下一页点击/等待逻辑中发生 NoSuchElementException: {nse}", exc_info=True)
        return False
    except TimeoutException: 
        logger.warning("等待页面导航超时（陈旧状态或新图片可见性）。可能是章节末尾或加载缓慢。")
        try: 
            if driver.find_element(By.XPATH, "//div[@id='pagination']//span[contains(@class, 'disabled') and (contains(text(), '下一页'))]").is_displayed():
                logger.info("通过查找已禁用的“下一页”span确认已到章节末尾。")
        except NoSuchElementException:
            logger.info("超时后未找到已禁用的“下一页”span。")
        return False 
    except Exception as e: 
        logger.error(f"点击“下一页”或等待导航时发生意外错误: {e}", exc_info=True)
        return False

def capture_chapter_images(
    start_url,
    image_id,
    urls_to_block,
    vertical_offset_compensation,
    base_output_dir="manga_chapters"
):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--force-device-scale-factor=1")
    initial_window_width = 1920 
    initial_window_height = 1080
    chrome_options.add_argument(f"--window-size={initial_window_width},{initial_window_height}")

    driver = None
    chapter_fully_captured = True # 初始化成功标志
    try:
        logger.info("正在初始化Chrome驱动程序以捕获章节...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 60) 

        if urls_to_block:
            logger.info(f"正在设置URL拦截: {urls_to_block}")
            driver.execute_cdp_cmd('Network.enable', {})
            driver.execute_cdp_cmd('Network.setBlockedURLs', {'urls': urls_to_block})

        logger.info(f"正在访问起始URL: {start_url}")
        driver.get(start_url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info("初始页面已加载。")

        match = re.search(r'/(\d+)\.html$', start_url)
        chapter_id_str = match.group(1) if match else "未知章节"
        chapter_output_dir = base_output_dir # 直接使用 base_output_dir
        os.makedirs(chapter_output_dir, exist_ok=True)
        logger.info(f"图片输出目录: {chapter_output_dir}") # 更新日志信息

        current_page_number = 1
        max_pages_to_try = 1000

        while current_page_number <= max_pages_to_try:
            logger.info(f"--- 正在处理第 {current_page_number} 页 ---")
            
            if not capture_single_page_image(
                driver,
                wait,
                image_id,
                vertical_offset_compensation,
                chapter_output_dir,
                current_page_number
            ):
                logger.warning(f"捕获第 {current_page_number} 页图片失败。停止此章节处理。")
                chapter_fully_captured = False # 标记章节未完全捕获
                break
            
            time.sleep(1)

            if not click_next_page_button(driver, wait, image_id):
                logger.info(f"在第 {current_page_number} 页后无法导航到下一页。假定已到章节末尾。")
                break
            
            current_page_number += 1

            if current_page_number % 30 == 0:
                logger.info(f"已处理 {current_page_number} 页，暂停10秒。")
                time.sleep(10)

            if current_page_number > max_pages_to_try:
                logger.warning(f"已达到最大尝试页数 ({max_pages_to_try})。停止处理。")
                break
        
        logger.info(f"章节捕获尝试完成。图片保存在 {chapter_output_dir}")

    except WebDriverException as e_wd:
        logger.error(f"章节捕获过程中发生WebDriver错误: {e_wd}", exc_info=True)
        chapter_fully_captured = False # 确保在WebDriver初始化或使用中出错时标记失败
    except Exception as e:
        logger.error(f"章节捕获过程中发生意外错误: {e}", exc_info=True)
        chapter_fully_captured = False # 确保在其他意外错误时标记失败
    finally:
        if driver:
            driver.quit()
            logger.info("浏览器已关闭。")
    return chapter_fully_captured # 返回捕获状态

# --- 配置变量，供脚本独立运行时使用，也可被其他模块导入 ---
target_image_id = "mangaFile"
blocked_urls = [
    "*doubleclick.net*", "*googleadservices.com*", "*googlesyndication.com*",
    "*adservice.google.com*", "*sitemaji.com*", "*exdynsrv.com*",
    "*google-analytics.com*", "*googletagmanager.com*"
]
vertical_offset = 0

if __name__ == "__main__":
    target_start_url = "https://www.manhuagui.com/comic/31550/435127.html"
    # target_image_id, blocked_urls, vertical_offset 现在是全局变量

    capture_chapter_images(
        start_url=target_start_url,
        image_id=target_image_id, # 使用全局变量
        urls_to_block=blocked_urls, # 使用全局变量
        vertical_offset_compensation=vertical_offset, # 使用全局变量
        base_output_dir="./qwq/downloaded_manga"
    )