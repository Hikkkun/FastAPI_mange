import httpx
from bs4 import BeautifulSoup

from ..utils.f2b import FB2Builder

headers = {
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language':'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
}

async def download(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    
    title = soup.find('span', {'class': 'title'}).text
    header = soup.find('meta', {'name': 'description'}).get('content')
    
    fb2 = FB2Builder(title)
    chapter = fb2.add_section(header)
    
    divs = soup.find('div', {'id': 'arrticle'}).find_all('p')
    for paragraph in divs:
        fb2.add_paragraph(chapter, paragraph.text)
        fb2.add_empty_line(chapter)     
        
    content = fb2.generate()
    return content