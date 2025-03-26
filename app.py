from fastapi import FastAPI, Query, HTTPException
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

# Initialize FastAPI app
app = FastAPI(title="Admission Announcements API")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scraper Functions

def scrape_bangalore_notifications() -> List[Dict]:
    """Scrape notifications from Bangalore University."""
    url = "https://bangaloreuniversity.karnataka.gov.in/notifications"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching Bangalore University notifications from {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    notifications = []
    container = soup.find('div', class_='container')
    if container:
        unordered_list = container.find('ul')
        if unordered_list:
            for item in unordered_list.find_all('li', recursive=False):
                link_tag = item.find('a')
                if link_tag and link_tag.get('href'):
                    title = link_tag.text.strip() or "Untitled"
                    link = urljoin(url, link_tag['href'])
                    notifications.append({
                        "university": "Bangalore",
                        "title": title,
                        "description": None,
                        "link": link
                    })
                else:
                    title = item.text.strip() or "Untitled"
                    notifications.append({
                        "university": "Bangalore",
                        "title": title,
                        "description": None,
                        "link": None
                    })
    return notifications

def scrape_goa_notifications() -> List[Dict]:
    """Scrape announcements from Goa University."""
    url = "https://www.unigoa.ac.in/systems/c/admissions/announcementsnotices.html"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching Goa University announcements from {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    notifications = []
    inside_wrapper = soup.find('div', class_='details1')
    if inside_wrapper:
        details1_left = inside_wrapper.find('div', class_='details1_left')
        if details1_left:
            for h4 in details1_left.find_all('h4'):
                title = h4.text.strip() or "Untitled"
                next_element = h4.find_next_sibling()
                details = (
                    [li.text.strip() for li in next_element.find_all('li')]
                    if next_element and next_element.name == 'ul'
                    else []
                )
                notifications.append({
                    "university": "Goa",
                    "title": title,
                    "details": details
                })
    return notifications

def scrape_mumbai_notifications() -> List[Dict]:
    """Scrape notifications from Mumbai University."""
    url = "https://mu.ac.in/department-announcements"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching Mumbai University notifications from {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    notifications = []
    list_items = soup.select('#main .entry-content .wpb_text_column ul li')
    for li in list_items:
        a_tag = li.find('a')
        if a_tag and a_tag.get('href'):
            title = a_tag.text.strip() or "Untitled"
            link = urljoin(url, a_tag['href'])
            notifications.append({
                "university": "Mumbai",
                "title": title,
                "link": link
            })
        else:
            title = li.text.strip() or "Untitled"
            notifications.append({
                "university": "Mumbai",
                "title": title,
                "link": None
            })
    return notifications

# API Endpoints

@app.get("/", summary="API Root")
async def root():
    """Provides a welcome message for the API."""
    return {"message": "Welcome to the Admission Announcements API"}

@app.get("/health", summary="Health Check")
async def health_check():
    """Verifies the API's availability."""
    return {"status": "ok"}

@app.get("/universities", summary="Get Supported Universities")
async def get_universities():
    """Returns a list of supported universities."""
    return {"data": ["Bangalore", "Goa", "Mumbai"]}

@app.get("/announcements", summary="Get All Announcements")
async def get_all_announcements(
    limit: int = Query(100, ge=1, description="Number of announcements to return"),
    offset: int = Query(0, ge=0, description="Number of announcements to skip")
):
    """Retrieves all announcements from all universities with pagination."""
    try:
        bangalore = scrape_bangalore_notifications()
        goa = scrape_goa_notifications()
        mumbai = scrape_mumbai_notifications()
        all_announcements = bangalore + goa + mumbai
        
        if not all_announcements:
            raise HTTPException(status_code=404, detail="No announcements found")
        
        total = len(all_announcements)
        paginated = all_announcements[offset:offset + limit]
        return {
            "data": paginated,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error in get_all_announcements: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/announcements/{university}", summary="Get Announcements by University")
async def get_university_announcements(
    university: str,
    limit: int = Query(100, ge=1, description="Number of announcements to return"),
    offset: int = Query(0, ge=0, description="Number of announcements to skip")
):
    """Retrieves announcements from a specific university with pagination."""
    scrapers = {
        "bangalore": scrape_bangalore_notifications,
        "goa": scrape_goa_notifications,
        "mumbai": scrape_mumbai_notifications
    }
    university_key = university.lower()
    if university_key not in scrapers:
        raise HTTPException(status_code=404, detail=f"University '{university}' not found")
    
    try:
        announcements = scrapers[university_key]()
        if not announcements:
            raise HTTPException(status_code=404, detail=f"No announcements found for {university}")
        
        total = len(announcements)
        paginated = announcements[offset:offset + limit]
        return {
            "data": paginated,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error in get_university_announcements for {university}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)