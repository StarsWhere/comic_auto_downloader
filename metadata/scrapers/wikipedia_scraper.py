import requests
from bs4 import BeautifulSoup
import json
import re
from ..config import WIKIPEDIA_API_URL, HEADERS

# --- Wikipedia Scraper Functions ---

def wikipedia_search_page(term):
    params = {"action": "query", "list": "search", "srsearch": term, "srlimit": 5, "format": "json"}
    print(f"Searching Wikipedia: {WIKIPEDIA_API_URL} with term '{term}'")
    try:
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        search_results_json = response.json()
        
        results = []
        if search_results_json.get("query", {}).get("search"):
            for item in search_results_json["query"]["search"]:
                page_title = item["title"]
                page_url = f"https://zh.wikipedia.org/wiki/{requests.utils.quote(page_title)}"
                snippet = BeautifulSoup(item.get("snippet", ""), 'html.parser').text 
                results.append({'title': page_title, 'url': page_url, 'snippet': snippet, 'source': 'wikipedia'})
        return results
    except requests.exceptions.RequestException as e:
        print(f"Error searching Wikipedia API: {e}")
        return []
    except json.JSONDecodeError:
        print("Error decoding Wikipedia API search response.")
        return []

def wikipedia_get_page_metadata(page_url):
    if not page_url: return None
    print(f"Fetching Wikipedia page: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metadata = {'source_url_wikipedia': page_url}
        page_title_tag = soup.select_one('h1#firstHeading')
        metadata['title_wikipedia'] = page_title_tag.text.strip() if page_title_tag else 'N/A'

        infobox = soup.find('table', class_=lambda x: x and 'infobox' in x)
        if not infobox:
            print("Infobox not found on Wikipedia page.")
            return metadata 

        metadata['infobox_image_urls_wikipedia'] = []
        image_links = infobox.select('a.image img')
        for img_tag in image_links:
            if img_tag and img_tag.has_attr('src'):
                img_src = img_tag['src']
                if img_src.startswith('//'): img_src = 'https:' + img_src
                if img_src not in metadata['infobox_image_urls_wikipedia']:
                    metadata['infobox_image_urls_wikipedia'].append(img_src)
        
        other_img_tags = infobox.select('td img') 
        for img_tag in other_img_tags:
            if img_tag and img_tag.has_attr('src'):
                img_src = img_tag['src']
                if any(p in img_src for p in ['/Icon_', '/Flag_of_', 'icon_']) or (img_tag.has_attr('width') and int(img_tag['width']) < 50):
                    continue 
                if img_src.startswith('//'): img_src = 'https:' + img_src
                is_already_in_a_image = any(parent_a and 'image' in parent_a.get('class', []) for parent_a in img_tag.find_parents('a'))
                if img_src not in metadata['infobox_image_urls_wikipedia'] and not is_already_in_a_image:
                     metadata['infobox_image_urls_wikipedia'].append(img_src)
        
        rows = infobox.find_all('tr')
        for row in rows:
            header_tag = row.find('th')
            data_tag = row.find('td')
            if header_tag and data_tag:
                key = header_tag.text.strip()
                for s in data_tag(['script', 'style']): s.decompose()
                list_items = data_tag.find_all('li')
                if list_items:
                    value = [item.text.strip() for item in list_items if item.text.strip()]
                else:
                    for br in data_tag.find_all('br'): br.replace_with(', ')
                    value = data_tag.text.strip()
                
                if isinstance(value, list) and len(value) == 1: value = value[0]
                
                clean_value = ""
                if isinstance(value, str):
                    clean_value = re.sub(r'\[\d+\]', '', requests.utils.unquote(value)).strip()
                    clean_value = re.sub(r'\s+', ' ', clean_value).strip()
                elif isinstance(value, list):
                    clean_value = []
                    for item_val in value:
                        item_cleaned = re.sub(r'\[\d+\]', '', requests.utils.unquote(item_val)).strip()
                        item_cleaned = re.sub(r'\s+', ' ', item_cleaned).strip()
                        if item_cleaned: clean_value.append(item_cleaned)
                    if not clean_value: 
                        fallback_text = data_tag.text.strip()
                        clean_value = re.sub(r'\[\d+\]', '', fallback_text).strip()
                        clean_value = re.sub(r'\s+', ' ', clean_value).strip()

                if key and (clean_value or isinstance(clean_value, list) and clean_value):
                    metadata[f"{key}_wikipedia"] = clean_value
        return metadata
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wikipedia page content: {e}")
        return None
    except Exception as e:
        print(f"An error occurred during Wikipedia page parsing: {e}")
        return None