from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from urllib.parse import urlparse
import tempfile
from .handlers import ranobe_me, ranobehub, ranobelib, ranobepoisk, ranobes

router = APIRouter()

# Словарь с поддерживаемыми доменами и соответствующими функциями загрузки
domain_downloaders = {
    'ranobe.me': ranobe_me.download,
    'ranobehub.org': ranobehub.download,
    'ranobelib.org': ranobelib.download,
    'ranobepoisk.ru': ranobepoisk.download,
    'ranobes.com': ranobes.download,
}

@router.get('/api/ranobe/download/')
async def ranobe_download(href: str):
    if not href:
        raise HTTPException(status_code=400, detail="Missing 'href' parameter")

    parsed_url = urlparse(href)
    domain = parsed_url.netloc

    download_func = domain_downloaders.get(domain)
    if not download_func:
        raise HTTPException(status_code=400, detail=f"Unsupported domain: {domain}")

    fb2_content = await download_func(href)
    if not fb2_content:
        raise HTTPException(status_code=500, detail=f"Failed to download '{href}'")

    # Использование временного файла для хранения загруженного контента
    with tempfile.NamedTemporaryFile(suffix=".fb2", delete=False) as tmp_file:
        tmp_file.write(fb2_content.encode('utf-8'))
        tmp_file_path = tmp_file.name

    return FileResponse(tmp_file_path, media_type='application/xml', filename="ranobe.fb2")