import httpx
from bs4 import BeautifulSoup

from ..utils.f2b import FB2Builder

async def download(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    
    title = soup.find_all('div', {'class': 'reader-header-action__text'})[0].text
    header = soup.find_all('div', {'class': 'reader-header-action__text'})[1].text
    
    paragraphs = soup.find('div', {'class': 'container'}).find_all('p', recursive=False) if soup.find('div', {'class': 'container'}) else []
    
    fb2 = FB2Builder(title)
    chapter = fb2.add_section(header)
    
    for paragraph in paragraphs:
        fb2.add_paragraph(chapter, paragraph.text)
        fb2.add_empty_line(chapter)
    
    content = fb2.generate()
    return content