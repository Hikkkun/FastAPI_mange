import httpx
from bs4 import BeautifulSoup
from typing import Optional

from ..utils.f2b import FB2Builder

async def download(url) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.find('title').text.split(' / ')[0].strip()
    header = soup.find('h1', {'class': 'header'}).text.strip()
    
    fb2 = FB2Builder(title)
    chapter = fb2.add_section(header)
    
    container = soup.find('div', class_='ui text container', attrs={'data-container': True})
    await process_container(container, fb2, chapter)

    content = fb2.generate() # Генерируем контент FB2
    return content

async def download_image(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
    return response

async def process_container(container, fb2, chapter):
    elements = []
    for tag in container.contents:
        elements.append(tag)

    for element in elements:
        if element.name == 'p':
            images = element.find_all('img')
            if images:
                for img in images:
                    media_id = img['data-media-id']
                    img_url = f'https://ranobehub.org/api/media/{media_id}'
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(img_url)
                        response.raise_for_status()
                            
                    fb2.add_image(chapter, media_id)
                    fb2.add_binary(chapter, media_id, response)
            else:
                fb2.add_paragraph(chapter, element.text)    

            fb2.add_empty_line(chapter)