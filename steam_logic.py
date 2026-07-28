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
                        
                        # Проверяем, есть ли информация об играх
                        # Если num_games_owned = 0, но автор написал много отзывов - вероятно, профиль скрыт
                        games_owned = r['author'].get('num_games_owned', 0)
                        reviews_posted = r['author'].get('num_reviews', 0)
                        
                        # Признак скрытого профиля: 0 игр, но есть отзывы
                        is_private = (games_owned == 0 and reviews_posted > 0)
                        
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
                            'Скрытый профиль': is_private,  # 👈 ДОБАВЛЕНО
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
    
    def _calculate_group_stats(self, df, group_column, group_name):
        """Универсальный метод для расчета статистики по группам"""
        df_copy = df.copy()
        df_copy['Группа'] = df_copy[group_column]
        
        stats = df_copy.groupby(['Группа', 'Тип отзыва']).size().unstack(fill_value=0)
        
        stats = stats.rename(columns={
            'Положительный': 'Положительные',
            'Отрицательный': 'Отрицательные'
        })
        
        stats['Кол-во отзывов'] = stats['Положительные'] + stats['Отрицательные']
        total_reviews = stats['Кол-во отзывов'].sum()
        stats['% от общего числа'] = (stats['Кол-во отзывов'] / total_reviews * 100).round(2)
        stats['% положительных от группы'] = (stats['Положительные'] / stats['Кол-во отзывов'] * 100).round(2)
        stats['% отрицательных от группы'] = (stats['Отрицательные'] / stats['Кол-во отзывов'] * 100).round(2)
        
        stats = stats.reset_index()
        stats = stats.rename(columns={'Группа': group_name})
        stats = stats[[group_name, 'Кол-во отзывов', 'Положительные', 'Отрицательные', 
                       '% от общего числа', '% положительных от группы', '% отрицательных от группы']]
        
        # Сортируем группы в логическом порядке
        order = {
            'Группа часов': ['0-5 часов', '5-20 часов', '20+ часов'],
            'Кол-во отзывов автора': ['0 отзывов', '1-5 отзывов', '6-20 отзывов', '20+ отзывов'],
            'Кол-во игр автора': ['Скрытый профиль', '0 игр', '1-10 игр', '11-50 игр', '51-200 игр', '200+ игр']
        }
        
        if group_name in order:
            stats['sort_order'] = stats[group_name].apply(
                lambda x: order[group_name].index(x) if x in order[group_name] else 999
            )
            stats = stats.sort_values('sort_order').drop(columns=['sort_order'])
        
        return stats
    
    def calculate_hours_stats(self, df):
        """Рассчитывает статистику по группам часов"""
        def get_hours_group(hours):
            if hours < 5:
                return '0-5 часов'
            elif 5 <= hours < 20:
                return '5-20 часов'
            else:
                return '20+ часов'
        
        df['Группа часов'] = df['Часов наиграно'].apply(get_hours_group)
        return self._calculate_group_stats(df, 'Группа часов', 'Группа часов')
    
    def calculate_reviews_count_stats(self, df):
        """Рассчитывает статистику по группам количества отзывов автора"""
        def get_reviews_group(count):
            if count == 0:
                return '0 отзывов'
            elif 1 <= count <= 5:
                return '1-5 отзывов'
            elif 6 <= count <= 20:
                return '6-20 отзывов'
            else:
                return '20+ отзывов'
        
        df['Кол-во отзывов автора'] = df['Кол-во отзывов'].apply(get_reviews_group)
        return self._calculate_group_stats(df, 'Кол-во отзывов автора', 'Кол-во отзывов автора')
    
    def calculate_games_count_stats(self, df):
        """Рассчитывает статистику по группам количества игр автора"""
        def get_games_group(row):
            # Если профиль скрыт — отдельная группа
            if row.get('Скрытый профиль', False):
                return 'Скрытый профиль'
            
            count = row['Кол-во игр']
            if count == 0:
                return '0 игр'
            elif 1 <= count <= 10:
                return '1-10 игр'
            elif 11 <= count <= 50:
                return '11-50 игр'
            elif 51 <= count <= 200:
                return '51-200 игр'
            else:
                return '200+ игр'
        
        df['Кол-во игр автора'] = df.apply(get_games_group, axis=1)
        return self._calculate_group_stats(df, 'Кол-во игр автора', 'Кол-во игр автора')
    
    def save_to_excel(self, reviews, appid, game_name=None):
        """Сохраняет отзывы и статистику в Excel (6 листов)"""
        df = pd.DataFrame(reviews)
        
        # Делаем гиперссылки
        def make_hyperlink(row):
            return f'=HYPERLINK("{row["Ссылка на отзыв"]}", "{row["Автор"]}")'
        df['Ссылка на отзыв'] = df.apply(make_hyperlink, axis=1)
        df.drop(columns=['Автор'], inplace=True)

        if 'Скрытый профиль' in df.columns:
            df.drop(columns=['Скрытый профиль'], inplace=True)
        
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
        
        # ---- ЛИСТ 4: Статистика по количеству отзывов автора ----
        reviews_count_stats = self.calculate_reviews_count_stats(df)
        
        # ---- ЛИСТ 5: Статистика по количеству игр автора ----
        games_count_stats = self.calculate_games_count_stats(df)
        
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
        
        # Сохраняем с 5 листами
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Отзывы', index=False)
            lang_stats.to_excel(writer, sheet_name='Статистика по языкам', index=False)
            hours_stats.to_excel(writer, sheet_name='Статистика по часам', index=False)
            reviews_count_stats.to_excel(writer, sheet_name='Статистика по отзывам автора', index=False)
            games_count_stats.to_excel(writer, sheet_name='Статистика по играм автора', index=False)
        
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