import re
import os
import requests

# --- Helper Functions ---
def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.replace(' ', '_')
    return name

def download_image(url, filepath, source_name, headers):
    if not url or url == 'N/A':
        print(f"Skipping download for {source_name} image: No URL provided.")
        return False
    print(f"Downloading {source_name} image from: {url} to {filepath}")
    try:
        img_response = requests.get(url, headers=headers, stream=True, timeout=20)
        img_response.raise_for_status()
        with open(filepath, 'wb') as f_img:
            for chunk in img_response.iter_content(chunk_size=8192):
                f_img.write(chunk)
        print(f"{source_name} image downloaded successfully to: {filepath}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {source_name} image ({url}): {e}")
        return False
    except Exception as e:
        print(f"Error saving {source_name} image ({url}): {e}")
        return False

def select_from_results(results, source_name):
    if not results:
        print(f"No results found from {source_name}.")
        return None
    if len(results) == 1:
        print(f"Automatically selected the only result from {source_name}: {results[0]['title']}")
        return results[0]

    print(f"\nMultiple results found from {source_name}. Please choose one:")
    for i, item in enumerate(results):
        print(f"{i + 1}. {item['title']} ({item.get('url', 'N/A')}) {item.get('type', '')} {item.get('snippet','')[:100]+'...' if item.get('snippet') else ''}")
    
    while True:
        try:
            choice = input(f"Enter the number of your choice (1-{len(results)}), or 0 to skip {source_name}: ")
            choice_idx = int(choice)
            if 0 <= choice_idx <= len(results):
                if choice_idx == 0:
                    return None
                return results[choice_idx - 1]
            else:
                print("Invalid choice. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")