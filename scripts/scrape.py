import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime
from urllib.parse import quote

def append_to_json(data, filename):
    """Helper function to append data to JSON file"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results = []
        
        results.append(data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error saving to JSON: {e}")

def scrape_website(initial_url, first_link_selector, second_link_selector, final_element_selector, output_dir):
    """
    Scrape content by following two levels of links and extracting elements from final pages
    
    Args:
        initial_url (str): Starting URL
        first_link_selector (str): CSS selector for first level links
        second_link_selector (str): CSS selector for second level links
        final_element_selector (str): CSS selector for content to extract
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(initial_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        first_level_links = soup.select(first_link_selector)
        print(f"Found {len(first_level_links)} first level links")
        if not first_level_links:
            print("No first level links found")
            return
        
        successful_scrapes = 0
        for first_link in first_level_links:
            first_url = first_link.get('href')
            if not first_url:
                continue
                
            if not first_url.startswith('http'):
                first_url = requests.compat.urljoin(initial_url, first_url)
            
            first_url = quote(first_url, safe=':/?=&')
            time.sleep(2)
            
            try:
                response = requests.get(first_url, headers=headers)
                response.raise_for_status()
                second_soup = BeautifulSoup(response.text, 'html.parser')
                second_link = second_soup.select_one(second_link_selector)
                if not second_link:
                    continue
                print(f"Processing: {second_link.text.strip()}")
                second_url = second_link.get('href')
                if not second_url:
                    continue
                    
                if not second_url.startswith('http'):
                    second_url = requests.compat.urljoin(first_url, second_url)
                
                second_url = quote(second_url, safe=':/?=&')
                time.sleep(2)
                
                final_response = requests.get(second_url, headers=headers)
                final_response.raise_for_status()
                final_soup = BeautifulSoup(final_response.text, 'html.parser')
                final_element = final_soup.select_one(final_element_selector)
                if final_element:
                    movie_title = first_link.text.strip()
                    safe_title = "".join(c for c in movie_title if c.isalnum() or c in (' ', '-'))
                    output_file = os.path.join(output_dir, f"{safe_title}.json")
                    
                    movie_data = {
                        'movie_title': movie_title,
                        'script_url': second_url,
                        'content': final_element.text.strip()
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(movie_data, f, indent=2, ensure_ascii=False)
                        
                    successful_scrapes += 1
                    print(f"Successfully saved: {movie_title}")
                
            except Exception as e:
                print(f"Error processing {first_url}: {e}")
                continue
                
        return successful_scrapes
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0

if __name__ == "__main__":
    initial_url = "https://imsdb.com/all-scripts.html"
    first_link_selector = "p a"
    second_link_selector = "p a"
    final_element_selector = "pre"
    
    output_dir = "../movie_scripts"
    os.makedirs(output_dir, exist_ok=True)
    
    successful_scrapes = scrape_website(
        initial_url, 
        first_link_selector, 
        second_link_selector, 
        final_element_selector,
        output_dir
    )
    
    print(f"\nCompleted scraping with {successful_scrapes} successful saves to {output_dir}")