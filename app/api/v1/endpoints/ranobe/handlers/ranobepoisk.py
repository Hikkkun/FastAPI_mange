import httpx
from bs4 import BeautifulSoup

from ..utils.f2b import FB2Builder

headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
}

async def download(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.h1.a.text.strip()
    header = soup.h1.text.strip().replace(title, '').strip()
    
    fb2 = FB2Builder(title)
    chapter = fb2.add_section(header)
    
    divs = soup.find('div', {'class': 'py-4'}).find('div', {'class': 'chapter-text-container'}).find_all('p')
    for paragraph in divs:
        fb2.add_paragraph(chapter, paragraph.text)
        fb2.add_empty_line(chapter)     
        
    content = fb2.generate()
    return content