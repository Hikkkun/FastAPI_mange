import httpx
import asyncio
import logging
import socket
import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.redis.redis_client import get_redis

router = APIRouter()

# Настройка логгера
logger = logging.getLogger(__name__)
#logging.getLogger("httpx").setLevel(logging.WARNING)  # Уменьшаем уровень логгирования для httpx, чтобы избежать лишних сообщений

# Настройки
URL = "https://api.senkuro.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
}

async def fetch(payload: dict, max_retries: int = 15, backoff_factor: float = 0.5, timeout: int = 60) -> dict:
    """
    Выполняет асинхронный HTTP-запрос с повторными попытками при ошибках.

    :param payload: Данные для отправки в теле запроса.
    :param max_retries: Максимальное количество попыток.
    :param backoff_factor: Коэффициент для экспоненциальной задержки между попытками.
    :param timeout: Тайм-аут запроса в секундах.
    :return: Ответ сервера в формате JSON.
    :raises Exception: Если достигнуто максимальное число попыток.
    """
    retry_count = 0

    while retry_count < max_retries:
        async with httpx.AsyncClient(headers=HEADERS, timeout=timeout) as client:
            try:
                response = await client.post(url=URL, json=payload)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Лимит запросов (Too Many Requests)
                    retry_count += 1
                    logger.warning(f"Ошибка HTTP (429): {e}. Повторная попытка через {backoff_factor * retry_count} секунд...")
                    await asyncio.sleep(backoff_factor * retry_count)  # Экспоненциальный бэкофф
                else:
                    raise e

            except (httpx.ConnectTimeout, httpx.TimeoutException, httpx.RequestError) as e:
                retry_count += 1
                logger.error(f"Ошибка соединения или тайм-аута: {e}. Повторная попытка через {backoff_factor * retry_count} секунд...")
                await asyncio.sleep(backoff_factor * retry_count)  # Экспоненциальный бэкофф

            except socket.gaierror as e:
                logger.error(f"Ошибка сокета: {e}. Невозможно разрешить {URL}.")
                break  # Прерываем цикл, если ошибка связана с разрешением DNS

            except Exception as e:
                logger.error(f"Произошла непредвиденная ошибка: {e}")
                raise e  # Перехватываем все остальные исключения

    logger.error(f"[Достигнуто максимальное число попыток] {payload}")  # Логируем достижение максимального числа попыток
    raise Exception(f"Достигнуто максимальное число попыток для {URL}")

@router.get("/api/manga/senkuro/search/")
async def title_search(text: str, redis = Depends(get_redis)):
    """
    Поиск манги по названию.

    :param text: Название манги для поиска.
    :param redis: Зависимость Redis для кэширования.
    :return: JSON-ответ с результатами поиска.
    """
    cache = await redis.get(text)
    if cache is not None:
        return JSONResponse(content=json.loads(cache), status_code=200)
    
    query = '''
        query searchTachiyomiManga($query: String) { 
            mangaTachiyomiSearch(query: $query) { 
                mangas { id slug originalName { lang content } titles { lang content } alternativeNames { lang content } cover { original { url } } } 
            } 
        }
    '''
    variables = {'query': text}
    
    response = await fetch({'query': query, 'variables': variables})
    if response:
        try:
            mangas = response.get('data', {}).get('mangaTachiyomiSearch', {}).get('mangas', [])
            if not mangas:
                return JSONResponse(content={"error": "No manga found"}, status_code=404)
            
            manga_list = []
            for manga in mangas:
                manga_data = {
                    "id": manga['id'],
                    "slug": manga['slug'],
                    "originalName": manga.get('originalName', {}).get('content', '').replace('"', '\''),
                    "titles": next(
                        (title['content'].replace('"', '\'') 
                         for title in manga.get('titles', []) if title['lang'] == 'RU'), None),
                    "alternativeNames": ", ".join(
                        (name.get('content', '').replace('"', '\'') 
                         for name in manga.get('alternativeNames', []))
                    ),
                    "cover": manga.get('cover', {}).get('original', {}).get('url')
                }
                manga_list.append(manga_data)
            await redis.setex(text, 3600, json.dumps(manga_list))
            
            return JSONResponse(content=manga_list, status_code=200)
        except KeyError as e:
            return JSONResponse(content={"error": f"Missing key in response: {e}"}, status_code=500)
        except Exception as e:
            return JSONResponse(content={"error": f"An unexpected error occurred: {e}"}, status_code=500)
    else:
        return JSONResponse(content={"error": "Request failed"}, status_code=500)

@router.get("/api/manga/senkuro/title/{slug:str}")
@router.get("/api/manga/senkuro/title/{slug:str}/{any}")
@router.get("/manga/{slug:str}")
@router.get("/manga/{slug:str}/{any}")
@router.get("/api/manga/{slug:str}")
@router.get("/api/manga/{slug:str}/{any}")
async def get_data(slug: str, redis = Depends(get_redis)):
    """
    Получение данных о манге по её slug.

    :param slug: Уникальный идентификатор манги.
    :param redis: Зависимость Redis для кэширования.
    :return: JSON-ответ с данными о манге.
    """
    cache = await redis.get(slug)
    if cache:
        return JSONResponse(content=json.loads(cache), status_code=200)

    # GraphQL запрос
    query = '''
        query($slug: String!) { 
            manga(slug: $slug) { 
                id slug localizations { lang description { __typename ... on TiptapNodeNestedBlock { content { ... on TiptapNodeText { text } } } } }
                titles { lang content } 
                alternativeNames { content } 
                chapters status translitionStatus 
                branches { id lang chapters } 
                genres { id titles { content } } 
                tags { id titles { content } } 
                cover { id blurhash original { url } } 
            } 
        }
    '''
    variables = {'slug': slug}
    response = await fetch({'query': query, 'variables': variables})
    
    if not response or 'data' not in response or not response['data'].get('manga'):
        return JSONResponse(content={"error": "Manga not found"}, status_code=404)
    
    # Извлечение данных
    manga = response['data']['manga']
    descriptions = [
        content.get("text", "")
        for loc in manga.get("localizations", [])
        if loc.get("lang") == "RU" and loc.get("description")
        for desc_block in loc["description"]
        for content in desc_block.get("content", [])
    ]
    all_text = " ".join(descriptions).replace("\\", "").replace('"', "'")

    data = {
        "id": manga.get("id"),
        "slug": manga.get("slug"),
        "description": all_text,
        "title_name": next((item.get("content") for item in manga.get("titles", []) if item.get("lang") == "RU"), None),
        "alternativeNames": ", ".join(item.get("content", "") for item in manga.get("alternativeNames", [])),
        "chapters": manga.get("chapters", 0),
        "status": manga.get("status", ""),
        "translitionStatus": manga.get("translitionStatus", ""),
        "branches": max(manga.get("branches", []), key=lambda x: x.get("chapters", 0), default={}).get("id", None),
        "genres": ", ".join(
            next((t.get("content", "") for t in item.get("titles", [])), "") 
            for item in manga.get("genres", [])
        ),
        "tags": ", ".join(
            next((t.get("content", "") for t in item.get("titles", [])), "") 
            for item in manga.get("tags", [])
        ),
        "cover": manga.get("cover", {}).get("original", {}).get("url", "")
    }
    
    if data:
        await redis.setex(slug, 3600, json.dumps(data))
        return JSONResponse(content=data, status_code=200)

    return JSONResponse(content={"error": "Request failed"}, status_code=500)

@router.get("/api/manga/senkuro/chapters/{slug}")
async def get_chapters(slug: str, redis = Depends(get_redis)):
    """
    Получение списка глав манги по её slug.

    :param slug: Уникальный идентификатор манги.
    :param redis: Зависимость Redis для кэширования.
    :return: JSON-ответ с данными о главах манги.
    """
    try:
        # Получаем данные о манге
        manga_response = await get_data(slug, redis)
        manga_data = json.loads(manga_response.body.decode("utf-8"))
    except Exception as e:
        # Логируем ошибку и возвращаем ответ с ошибкой
        logger.error(f"Ошибка при получении данных манги: {e}")
        return JSONResponse(content={"error": "Failed to fetch manga data"}, status_code=500)
    
    query = '''
        query($branchId: ID!, $after: String, $first: Int) { 
            mangaChapters(branchId: $branchId, after: $after, first: $first) { 
                pageInfo { endCursor hasNextPage } 
                edges { node { slug id name number volume } } 
            } 
        }
    '''
    variables = {'branchId': manga_data['branches'], 'after': None, 'first': 100}
    chapters_list = []
    has_next_page = True
    
    while has_next_page:
        response = await fetch({'query': query, 'variables': variables})
        if response:
            page_info = response['data']['mangaChapters']['pageInfo']
            has_next_page = page_info['hasNextPage']
            variables['after'] = page_info['endCursor']
            
            for manga in response['data']['mangaChapters']['edges']:
                chapters = {
                    'id': manga['node']['id'],
                    'name': manga['node']['name'],
                    'number': manga['node']['number'],
                    'volume': manga['node']['volume'],
                    'slug': manga['node']['slug'], 
                }
                chapters_list.append(chapters)
    
    if chapters_list:
        return JSONResponse(content=chapters_list, status_code=200)
    
    return JSONResponse(content={"error": "Request failed"}, status_code=500)

@router.get("/api/manga/senkuro/{slug}/{chapterId}")
@router.get("/api/manga/senkuro/images/{slug}/{chapterId}")
async def title_images(slug, chapterId:str, redis = Depends(get_redis)): 
    cache = await redis.get(f"{slug}_{chapterId}")
    if cache:
        return JSONResponse(content=json.loads(cache), status_code=200)
    
    try:
        # Получаем данные о манге
        manga_response = await get_data(slug, redis)
        manga_data = json.loads(manga_response.body.decode("utf-8"))
    except Exception as e:
        # Логируем ошибку и возвращаем ответ с ошибкой
        logger.error(f"Ошибка при получении данных манги: {e}")
        return JSONResponse(content={"error": "Failed to fetch manga data"}, status_code=500) 
    
    query = '''
        query fetchTachiyomiChapterPages($mangaId: ID!, $chapterId: ID!) { 
            mangaTachiyomiChapterPages(mangaId: $mangaId, chapterId: $chapterId) { pages { url } } 
        }
    '''
    variables = {'mangaId': manga_data.get('id'), 'chapterId': chapterId}
    
    response = await fetch({'query': query, 'variables': variables})
    if response:
        images = [image.get('url', '') for image in response.get('data', {}).get('mangaTachiyomiChapterPages', {}).get('pages', [])]
        await redis.setex(f"{slug}_{chapterId}", 3600, json.dumps({'links':images}))
        return JSONResponse(content={'links':images}, status_code=200)