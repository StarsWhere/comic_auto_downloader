import requests
from bs4 import BeautifulSoup
from ..config import BANGUMI_BASE_URL, HEADERS

# --- Bangumi Scraper Functions ---

def bangumi_search_subject(term):
    search_url = f"{BANGUMI_BASE_URL}/subject_search/{requests.utils.quote(term)}?cat=1" # cat=1 for Books (Manga)
    print(f"搜索 Bangumi：{search_url}")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = []
        search_items_container = soup.select_one('ul#browserItemList') # 查找包含所有条目的ul元素
        if search_items_container: # 如果找到了ul元素
            item_elements = search_items_container.select('li.item') # 选择ul下的所有li.item元素
            for item_element in item_elements: # 遍历每个li.item元素
                link_tag = item_element.select_one('h3 a.l') # 在当前li.item中查找h3下的a.l链接
                if link_tag and link_tag.has_attr('href') and link_tag['href'].startswith('/subject/'):
                    title = link_tag.text.strip()
                    url = BANGUMI_BASE_URL + link_tag['href']
                    small_tag = link_tag.find_next_sibling('small', class_='grey') # small_tag 是 a 标签的直接兄弟节点
                    if small_tag:
                        title += f" ({small_tag.text.strip()})"
                    
                    info_div = link_tag.find_parent('h3').find_next_sibling('p', class_='info') # info_div 是 h3 标签的兄弟节点
                    item_type = info_div.text.strip().split('/')[0].strip() if info_div else "Unknown Type"

                    # Since cat=1 already filters for books, we can be less strict here
                    # or simply add all results found under the 'li.item'
                    results.append({'title': title, 'url': url, 'type': item_type, 'source': 'bangumi'})
        
        if not results: 
            first_result_h3 = soup.find('h3')
            if first_result_h3:
                link_tag = first_result_h3.find('a', class_='l', href=lambda x: x and x.startswith('/subject/'))
                if link_tag:
                    title = link_tag.text.strip()
                    small_tag = link_tag.find_next_sibling('small', class_='grey')
                    if small_tag:
                        title += f" ({small_tag.text.strip()})"
                    results.append({'title': title, 'url': BANGUMI_BASE_URL + link_tag['href'], 'type': 'Manga/Book (assumed)', 'source': 'bangumi'})

        return results
    except requests.exceptions.RequestException as e:
        print(f"搜索 Bangumi 时出错：{e}")
        return []


def bangumi_get_subject_details(subject_url):
    if not subject_url: return None
    print(f"从 Bangumi 获取主题详情：{subject_url}")
    try:
        response = requests.get(subject_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        details = {'source_url_bangumi': subject_url}

        title_tag = soup.select_one('h1#headerSubject a')
        if title_tag:
            details['title_bangumi'] = title_tag.text.strip()
            if title_tag.small:
                details['title_original_bangumi'] = title_tag.small.text.strip()

        cover_link_tag = soup.select_one('div.infobox a.thickbox.cover')
        if cover_link_tag and cover_link_tag.has_attr('href'):
            cover_url = cover_link_tag['href']
            if cover_url.startswith('//'): cover_url = 'https:' + cover_url
            details['cover_image_url_bangumi'] = cover_url
        else:
            cover_img_tag = soup.select_one('div.infobox img.cover') 
            if cover_img_tag and cover_img_tag.has_attr('src'):
                cover_url = cover_img_tag['src']
                if cover_url.startswith('//'): cover_url = 'https:' + cover_url
                details['cover_image_url_bangumi'] = cover_url


        summary_tag = soup.select_one('div#subject_summary')
        if summary_tag:
            for br in summary_tag.find_all('br'): br.replace_with('\n')
            details['summary_bangumi'] = summary_tag.text.strip()

        tags = []
        tag_section = soup.select_one('div.subject_tag_section')
        if tag_section:
            tag_links = tag_section.select('a.l.meta span')
            for tag_span in tag_links: tags.append(tag_span.text.strip())
        details['tags_bangumi'] = tags

        score_tag = soup.select_one('span.number[property="v:average"]')
        if score_tag: details['rating_score_bangumi'] = score_tag.text.strip()
        
        votes_tag = soup.select_one('small.grey span[property="v:votes"]')
        if votes_tag: details['rating_votes_bangumi'] = votes_tag.text.strip()

        infobox_metadata = {}
        infobox_ul = soup.select_one('ul#infobox')
        if infobox_ul:
            for li in infobox_ul.find_all('li', recursive=False):
                tip_span = li.find('span', class_='tip')
                if tip_span:
                    key = tip_span.text.strip().replace(':', '').replace('：', '')
                    value_parts = []
                    current_node = tip_span.next_sibling
                    while current_node:
                        if isinstance(current_node, str): value_parts.append(current_node.strip())
                        elif current_node.name == 'a': value_parts.append(current_node.text.strip())
                        elif current_node.name == 'span' and 'tag' in current_node.get('class', []):
                            if not current_node.find_parent('li', class_='sub_container'):
                                value_parts.append(current_node.text.strip())
                        current_node = current_node.next_sibling
                    value = ' '.join(filter(None, value_parts)).strip()
                    
                    if "sub_group" in li.get('class', []):
                        group_tags = li.find_all('span', class_=lambda x: x and 'tag' in x and 'group_tag' in x and 'more' not in x)
                        value = [tag.text.strip() for tag in group_tags]

                    if key and value:
                        if key in infobox_metadata:
                            if not isinstance(infobox_metadata[key], list): infobox_metadata[key] = [infobox_metadata[key]]
                            if isinstance(value, list): infobox_metadata[key].extend(value)
                            else: infobox_metadata[key].append(value)
                        else: infobox_metadata[key] = value
            for k, v_list in infobox_metadata.items():
                if isinstance(v_list, list) and len(v_list) == 1: infobox_metadata[k] = v_list[0]
        details['infobox_bangumi'] = infobox_metadata
        return details
    except requests.exceptions.RequestException as e:
        print(f"获取 Bangumi 主题页面时出错：{e}")
        return None
    except Exception as e:
        print(f"解析 Bangumi 主题页面时发生错误：{e}")
        return None