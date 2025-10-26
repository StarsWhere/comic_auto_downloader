import re
import os
import requests
import logging

# --- Helper Functions ---
logger = logging.getLogger(__name__)

def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.replace(' ', '_')
    return name

def get_user_input(prompt, valid_inputs=None, case_sensitive=False):
    """
    统一的输入处理函数
    :param prompt: 提示信息
    :param valid_inputs: 有效的输入列表，如果为None则接受任何输入
    :param case_sensitive: 是否大小写敏感
    :return: 用户输入的字符串
    """
    while True:
        try:
            user_input = input(prompt).strip()
            if not user_input:
                logger.warning("输入不能为空，请重新输入。")
                continue

            if valid_inputs is not None:
                if not case_sensitive:
                    user_input_lower = user_input.lower()
                    valid_inputs_lower = [v.lower() for v in valid_inputs]
                    if user_input_lower not in valid_inputs_lower:
                        logger.warning(f"无效输入 '{user_input}'。有效选项：{valid_inputs}")
                        continue
                    # 返回原始大小写的匹配项
                    for original in valid_inputs:
                        if original.lower() == user_input_lower:
                            return original
                else:
                    if user_input not in valid_inputs:
                        logger.warning(f"无效输入 '{user_input}'。有效选项：{valid_inputs}")
                        continue
            return user_input
        except KeyboardInterrupt:
            logger.info("用户中断输入。")
            return None
        except EOFError:
            logger.info("输入流结束。")
            return None

def get_user_confirmation(prompt="请确认 (yes/no): ", default=None):
    """
    获取用户确认输入
    :param prompt: 提示信息
    :param default: 默认值 ('yes', 'no' 或 None)
    :return: True 或 False
    """
    valid_yes = ['yes', 'y', '是', '确认', '确定']
    valid_no = ['no', 'n', '否', '取消', '不']

    if default == 'yes':
        prompt += " (输入 yes/y/是/确认/确定 表示同意，其他表示不同意): "
    elif default == 'no':
        prompt += " (输入 no/n/否/取消/不 表示不同意，其他表示同意): "
    else:
        prompt += " (输入 yes/y/是/确认/确定 表示同意，no/n/否/取消/不 表示不同意): "

    while True:
        user_input = get_user_input(prompt)
        if user_input is None:
            return default == 'yes' if default else False

        user_input_lower = user_input.lower()

        if user_input_lower in [v.lower() for v in valid_yes]:
            return True
        elif user_input_lower in [v.lower() for v in valid_no]:
            return False
        elif default is not None and not user_input:
            return default == 'yes'
        else:
            logger.warning("请输入有效的确认词，如: yes/no, 是/否, 确认/取消 等。")

def select_from_results(results, source_name):
    if not results:
        logger.info(f"未从 {source_name} 找到结果。")
        return None
    if len(results) == 1:
        logger.info(f"自动选择 {source_name} 的唯一结果：{results[0]['title']}")
        return results[0]

    logger.info(f"\n从 {source_name} 找到多个结果，请选择一个：")
    for i, item in enumerate(results):
        logger.info(f"{i + 1}. {item['title']} ({item.get('url', 'N/A')}) {item.get('type', '')} {item.get('snippet','')[:100]+'...' if item.get('snippet') else ''}")

    while True:
        choice = get_user_input(f"输入您的选择编号 (1-{len(results)})，或输入 0 跳过 {source_name}：")
        if choice is None:
            return None
        try:
            choice_idx = int(choice)
            if 0 <= choice_idx <= len(results):
                if choice_idx == 0:
                    return None
                return results[choice_idx - 1]
            else:
                logger.warning("无效选择。请从列表中输入一个数字。")
        except ValueError:
            logger.warning("无效输入。请输入一个数字。")

def download_image(url, filepath, source_name, headers):
    if not url or url == 'N/A':
        logger.info(f"跳过下载 {source_name} 图片：未提供 URL。")
        return False
    logger.info(f"正在从 {url} 下载 {source_name} 图片到 {filepath}")
    try:
        img_response = requests.get(url, headers=headers, stream=True, timeout=20)
        img_response.raise_for_status()
        with open(filepath, 'wb') as f_img:
            for chunk in img_response.iter_content(chunk_size=8192):
                f_img.write(chunk)
        logger.info(f"{source_name} 图片下载成功到：{filepath}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"下载 {source_name} 图片时出错 ({url})：{e}")
        return False
    except Exception as e:
        logger.error(f"保存 {source_name} 图片时出错 ({url})：{e}")
        return False

def select_from_results(results, source_name):
    if not results:
        print(f"未从 {source_name} 找到结果。")
        return None
    if len(results) == 1:
        print(f"自动选择 {source_name} 的唯一结果：{results[0]['title']}")
        return results[0]

    print(f"\n从 {source_name} 找到多个结果，请选择一个：")
    for i, item in enumerate(results):
        print(f"{i + 1}. {item['title']} ({item.get('url', 'N/A')}) {item.get('type', '')} {item.get('snippet','')[:100]+'...' if item.get('snippet') else ''}")

    while True:
        try:
            choice = input(f"输入您的选择编号 (1-{len(results)})，或输入 0 跳过 {source_name}：")
            choice_idx = int(choice)
            if 0 <= choice_idx <= len(results):
                if choice_idx == 0:
                    return None
                return results[choice_idx - 1]
            else:
                print("无效选择。请从列表中输入一个数字。")
        except ValueError:
            print("无效输入。请输入一个数字。")