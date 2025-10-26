import requests
from bs4 import BeautifulSoup
import re
from ..config import BASE_URL_MANHUA, HEADERS

# --- Manhuagui Scraper Functions ---

def manhuagui_search_manga(manga_name):
    search_url = f"{BASE_URL_MANHUA}/s/{manga_name}.html"
    print(f"搜索 Manhuagui：{search_url}")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        seen_urls = set()
        
        search_containers = soup.select('div.book-result ul.book-list li dl.cf, div.book-result li, ul.book-list li, div.book-detail')

        for container in search_containers:
            dt_elements = container.select('dt') 
            for dt in dt_elements:
                main_a_tag = dt.find('a', recursive=False, href=lambda x: x and x.startswith('/comic/'))
                if not main_a_tag: 
                    main_a_tag = dt.find('a', title=True, href=lambda x: x and x.startswith('/comic/'))

                if main_a_tag:
                    title = main_a_tag.get('title', main_a_tag.text.strip())
                    url = main_a_tag.get('href')

                    if not url or not url.startswith('/comic/'):
                        continue
                    
                    full_url = BASE_URL_MANHUA + url
                    if full_url in seen_urls:
                        continue

                    small_tag = dt.find('small')
                    alias_text = ""
                    if small_tag and small_tag.find('a'):
                        alias_text = small_tag.find('a').text.strip()
                    elif small_tag: 
                        alias_text = small_tag.text.strip().replace('(', '').replace(')', '')

                    if alias_text and alias_text != title: 
                        title_display = f"{title} ({alias_text})"
                    else:
                        title_display = title
                    
                    if title and title != "详情": 
                        results.append({'title': title_display, 'url': full_url, 'source': 'manhuagui'})
                        seen_urls.add(full_url)

        if not results:
            general_links = soup.select('div.book-list li a[title][href^="/comic/"], div.book-detail dt a[title][href^="/comic/"]')
            for link_tag in general_links:
                title = link_tag.get('title')
                url = link_tag.get('href')
                full_url = BASE_URL_MANHUA + url
                if full_url in seen_urls:
                    continue
                if title and title != "详情":
                    results.append({'title': title, 'url': full_url, 'source': 'manhuagui'})
                    seen_urls.add(full_url)
        
        if not results:
            all_comic_links = soup.find_all('a', href=lambda h: h and h.startswith('/comic/'))
            for link_tag in all_comic_links:
                title_attr = link_tag.get('title')
                text_content = link_tag.text.strip()
                current_title = ""

                if title_attr and title_attr != "详情" and len(title_attr) > 1:
                    current_title = title_attr
                elif text_content and text_content != "详情" and len(text_content) > 1: 
                    current_title = text_content
                else:
                    continue

                full_url = BASE_URL_MANHUA + link_tag['href']
                if full_url in seen_urls:
                    continue
                
                if re.match(r"^(第\d+话|开始阅读|在线观看|最新章节)", current_title):
                    is_likely_main_result = link_tag.find_parent('dt') and link_tag.find_parent('dl') and link_tag.find_parent('li')
                    if not is_likely_main_result:
                        continue

                results.append({'title': current_title, 'url': full_url, 'source': 'manhuagui'})
                seen_urls.add(full_url)

        final_unique_results = []
        final_seen_urls = set()
        for res in results:
            if res['url'] not in final_seen_urls:
                final_unique_results.append(res)
                final_seen_urls.add(res['url'])
        
        return final_unique_results
    except requests.exceptions.RequestException as e:
        print(f"Manhuagui 搜索过程中出错：{e}")
        return []

def manhuagui_get_manga_details(manga_url):
    print(f"从 Manhuagui 获取详情：{manga_url}")
    try:
        response = requests.get(manga_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        details = {'source_url_manhuagui': manga_url}
        
        title_tag = soup.select_one('div.book-title h1')
        details['title_manhuagui'] = title_tag.text.strip() if title_tag else 'N/A'
        
        cover_img_tag = soup.select_one('div.book-cover img')
        details['cover_image_url_manhuagui'] = cover_img_tag['src'] if cover_img_tag and cover_img_tag.has_attr('src') else 'N/A'
        if details['cover_image_url_manhuagui'].startswith('//'):
            details['cover_image_url_manhuagui'] = 'https:' + details['cover_image_url_manhuagui']

        intro_tag = soup.select_one('#intro-all p') or soup.select_one('#intro-cut')
        details['introduction_manhuagui'] = intro_tag.text.strip() if intro_tag else 'N/A'

        detail_list_items = soup.select('ul.detail-list li')
        for item in detail_list_items:
            strong_tag = item.find('strong')
            if strong_tag:
                key = strong_tag.text.strip().replace('：', '')
                value_tag = strong_tag.next_sibling
                value = ''
                if value_tag and isinstance(value_tag, str):
                    value = value_tag.strip()
                elif item.find('a'):
                    value = ', '.join(a.text.strip() for a in item.find_all('a'))
                elif item.find('span', class_='red'):
                     value = item.find('span', class_='red').text.strip()
                     status_text_node = item.find('span', class_='red').parent.next_sibling
                     if status_text_node and isinstance(status_text_node, str):
                         value += status_text_node.strip()
                     status_link = item.find('a', class_='blue')
                     if status_link:
                         value += f" [{status_link.text.strip()}]({BASE_URL_MANHUA + status_link['href'] if status_link.has_attr('href') else ''})"
                         after_link_node = status_link.next_sibling
                         if after_link_node and isinstance(after_link_node, str):
                             value += after_link_node.strip()
                else:
                    value = item.text.replace(strong_tag.text, '').strip()
                details[f"{key}_manhuagui"] = value
        
        details['chapters_manhuagui'] = { '单话': [], '单行本': [], '番外篇': [] }
        chapter_types_map = { '单话': '单话', '单行本': '单行本', '番外篇': '番外篇' }
        current_chapter_type_key = None
        for element in soup.select('div.chapter.mt16 > *'):
            if element.name == 'h4' and element.find('span'):
                type_text = element.find('span').text.strip()
                if type_text in chapter_types_map:
                    current_chapter_type_key = chapter_types_map[type_text]
            elif element.name == 'div' and 'chapter-list' in element.get('class', []) and current_chapter_type_key:
                chapter_links_ul = element.find_all('ul')
                for ul_tag in chapter_links_ul:
                    links = ul_tag.find_all('a', href=lambda h: h and h.startswith('/comic/'))
                    for link in links:
                        chapter_title = link.get('title', link.text.strip())
                        chapter_url = link['href']
                        chapter_title = chapter_title.split('<i>')[0].strip()
                        if chapter_title.endswith('p') and chapter_title[:-1].isdigit():
                            for i in range(len(chapter_title) - 1, -1, -1):
                                if not chapter_title[i].isdigit() and chapter_title[i] != 'p':
                                    chapter_title = chapter_title[:i+1]
                                    break
                        details['chapters_manhuagui'][current_chapter_type_key].append({
                            'title': chapter_title,
                            'url': BASE_URL_MANHUA + chapter_url
                        })
        for chap_type in details['chapters_manhuagui']:
            unique_chaps = []
            seen_chap_urls = set()
            for chap in details['chapters_manhuagui'][chap_type]:
                if chap['url'] not in seen_chap_urls:
                    unique_chaps.append(chap)
                    seen_chap_urls.add(chap['url'])
            details['chapters_manhuagui'][chap_type] = unique_chaps
        return details
    except requests.exceptions.RequestException as e:
        print(f"Manhuagui 详情请求过程中出错：{e}")
        return None
    except Exception as e:
        print(f"解析 Manhuagui 详情时发生错误：{e}")
        return None