import asyncio
import aiohttp
import pandas as pd
from datetime import datetime

class SteamReviewsDownloader:
    """Класс для загрузки и обработки отзывов Steam"""
    
    def __init__(self):
        self.reviews = []
        self.total_reviews = 0
        self.available_reviews = None
        self.progress_callback = None
        self.game_name = None
    
    def set_progress_callback(self, callback):
        """Устанавливает функцию для обновления прогресса"""
        self.progress_callback = callback
    
    async def fetch_game_name(self, appid):
        """Получает название игры по AppID"""
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=russian"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                if str(appid) in data and data[str(appid)]['success']:
                    name = data[str(appid)]['data']['name']
                    self.game_name = name
                    return name
                return None
    
    async def fetch_total_reviews(self, appid):
        """Получает общее количество отзывов у игры"""
        url = f"https://store.steampowered.com/appreviews/{appid}"
        params = {
            'json': 1,
            'filter': 'all',
            'language': 'all',
            'day_range': 9223372036854775807,
            'review_type': 'all',
            'purchase_type': 'all',
            'num_per_page': 1,
            'cursor': '*',
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get('query_summary', {}).get('total_reviews', 0)
    
    async def download_reviews(self, appid, max_reviews, progress_callback=None):
        """Загружает отзывы и возвращает список"""
        reviews = []
        seen_ids = set()
        cursor = '*'
        headers = {"User-Agent": "Mozilla/5.0"}
        total_downloaded = 0
        
        async with aiohttp.ClientSession() as session:
            while len(reviews) < max_reviews:
                url = f"https://store.steampowered.com/appreviews/{appid}"
                params = {
                    'json': 1,
                    'filter': 'all',
                    'language': 'all',
                    'day_range': 9223372036854775807,
                    'review_type': 'all',
                    'purchase_type': 'all',
                    'num_per_page': 100,
                    'cursor': cursor,
                }
                async with session.get(url, params=params, headers=headers) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                
                batch_reviews = data.get('reviews', [])
                if not batch_reviews:
                    break
                
                for r in batch_reviews:
                    rid = r.get('recommendationid')
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        steamid = r['author']['steamid']
                        recommendationid = rid
                        review_url = f"https://steamcommunity.com/profiles/{steamid}/recommended/{appid}/#review_{recommendationid}"
                        review_text = r.get('review', '')
                        recommended = "Положительный" if r.get('voted_up', False) else "Отрицательный"
                        language = r.get('language', 'unknown')
                        
                        timestamp = r.get('timestamp_created', 0)
                        if timestamp:
                            date_created = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            date_created = 'unknown'
                        
                        helpful = r.get('votes_up', 0)
                        funny = r.get('votes_funny', 0)
                        games_owned = r['author'].get('num_games_owned', 0)
                        reviews_posted = r['author'].get('num_reviews', 0)
                        hours_played = r['author'].get('playtime_forever', 0) / 60
                        
                        reviews.append({
                            'Автор': steamid,
                            'Ссылка на отзыв': review_url,
                            'Отзыв': review_text,
                            'Тип отзыва': recommended,
                            'Язык': language,
                            'Дата создания': date_created,
                            'Helpful': helpful,
                            'Funny': funny,
                            'Кол-во игр': games_owned,
                            'Кол-во отзывов': reviews_posted,
                            'Часов наиграно': round(hours_played, 2),
                        })
                        
                        total_downloaded += 1
                        if progress_callback:
                            progress_callback(total_downloaded, max_reviews)
                        
                        if len(reviews) >= max_reviews:
                            break
                
                cursor = data.get('cursor')
                if not cursor:
                    break
        
        return reviews
    
    def calculate_hours_stats(self, df):
        """Рассчитывает статистику по группам часов"""
        df_copy = df.copy()
        
        def get_hours_group(hours):
            if hours < 5:
                return '0-5 часов'
            elif 5 <= hours < 20:
                return '5-20 часов'
            else:
                return '20+ часов'
        
        df_copy['Группа часов'] = df_copy['Часов наиграно'].apply(get_hours_group)
        
        hours_stats = df_copy.groupby(['Группа часов', 'Тип отзыва']).size().unstack(fill_value=0)
        
        hours_stats = hours_stats.rename(columns={
            'Положительный': 'Положительные',
            'Отрицательный': 'Отрицательные'
        })
        
        hours_stats['Кол-во отзывов'] = hours_stats['Положительные'] + hours_stats['Отрицательные']
        total_reviews = hours_stats['Кол-во отзывов'].sum()
        hours_stats['% от общего числа'] = (hours_stats['Кол-во отзывов'] / total_reviews * 100).round(2)
        hours_stats['% положительных от группы'] = (hours_stats['Положительные'] / hours_stats['Кол-во отзывов'] * 100).round(2)
        hours_stats['% отрицательных от группы'] = (hours_stats['Отрицательные'] / hours_stats['Кол-во отзывов'] * 100).round(2)
        
        hours_stats = hours_stats.reset_index()
        hours_stats = hours_stats[['Группа часов', 'Кол-во отзывов', 'Положительные', 'Отрицательные', 
                                   '% от общего числа', '% положительных от группы', '% отрицательных от группы']]
        
        return hours_stats
    
    def save_to_excel(self, reviews, appid, game_name=None):
        """Сохраняет отзывы и статистику в Excel (3 листа)"""
        df = pd.DataFrame(reviews)
        
        # Делаем гиперссылки
        def make_hyperlink(row):
            return f'=HYPERLINK("{row["Ссылка на отзыв"]}", "{row["Автор"]}")'
        df['Ссылка на отзыв'] = df.apply(make_hyperlink, axis=1)
        df.drop(columns=['Автор'], inplace=True)
        
        total_reviews = len(reviews)
        
        # ---- ЛИСТ 2: Статистика по языкам ----
        lang_stats = df.groupby('Язык').agg(
            кол_во_отзывов=('Язык', 'size'),
            положительных=('Тип отзыва', lambda x: (x == 'Положительный').sum()),
            отрицательных=('Тип отзыва', lambda x: (x == 'Отрицательный').sum())
        ).reset_index()
        
        lang_stats['% от общего числа'] = (lang_stats['кол_во_отзывов'] / total_reviews * 100).round(2)
        lang_stats['% положительных от языка'] = (lang_stats['положительных'] / lang_stats['кол_во_отзывов'] * 100).round(2)
        lang_stats['% отрицательных от языка'] = (lang_stats['отрицательных'] / lang_stats['кол_во_отзывов'] * 100).round(2)
        lang_stats = lang_stats.sort_values('кол_во_отзывов', ascending=False)
        lang_stats.columns = ['Язык', 'Кол-во отзывов', 'Положительные', 'Отрицательные', 
                              '% от общего числа', '% положительных от языка', '% отрицательных от языка']
        
        # ---- ЛИСТ 3: Статистика по часам ----
        hours_stats = self.calculate_hours_stats(df)
        
        # Формируем имя файла
        if game_name:
            invalid_chars = r'<>:"/\|?*'
            for char in invalid_chars:
                game_name = game_name.replace(char, '')
            if len(game_name) > 200:
                game_name = game_name[:200]
            filename = f"{game_name}.xlsx"
        else:
            filename = f"{appid}_reviews.xlsx"
        
        # Сохраняем с 3 листами
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Отзывы', index=False)
            lang_stats.to_excel(writer, sheet_name='Статистика по языкам', index=False)
            hours_stats.to_excel(writer, sheet_name='Статистика по часам', index=False)
        
        # Авто-подгонка ширины колонок
        try:
            from openpyxl import load_workbook
            wb = load_workbook(filename)
            for sheet in wb.worksheets:
                for column in sheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    sheet.column_dimensions[column_letter].width = adjusted_width
            wb.save(filename)
        except:
            pass
        
        return filename