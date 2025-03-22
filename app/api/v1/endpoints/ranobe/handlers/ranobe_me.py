import httpx
from bs4 import BeautifulSoup

from ..utils.f2b import FB2Builder


async def download(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    
    title = soup.select_one('div.MessageAloneHead a').text
    header = soup.select_one('div.ReadTextContainerIn h1').text
    
    paragraphs = [p for p in soup.find_all('p', {'class': 'fict'})]
    
    fb2 = FB2Builder(title)
    chapter = fb2.add_section(header)
    
    for index, paragraph in enumerate(paragraphs):
        if index != 0:
            fb2.add_paragraph(chapter, paragraph.text)
            fb2.add_empty_line(chapter)
    
    content = fb2.generate()
    
    return content