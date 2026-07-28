import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
from steam_logic import SteamReviewsDownloader


class SteamReviewsApp:
    def __init__(self, root):
        self.root = root
        self.downloader = SteamReviewsDownloader()
        self.available_reviews = None
        self.current_entry = None
        self.game_name = None  # 👈 Добавляем поле для названия игры
        
        self._setup_window(root)
        self._setup_styles()
        self._create_widgets()
        self._setup_bindings()
    
    def _setup_window(self, root):
        """Настройка окна"""
        root.title("Steam Reviews Downloader")
        root.geometry("590x360")
        root.resizable(False, False)
        root.configure(bg="#1e1e2f")
    
    def _setup_styles(self):
        """Настройка стилей"""
        style = ttk.Style(self.root)
        style.theme_use('clam')
        
        style.configure("TLabel",
                        background="#1e1e2f",
                        foreground="#e0e0e0",
                        font=("Segoe UI", 11))
        style.configure("TButton",
                        background="#4a4e69",
                        foreground="#e0e0e0",
                        font=("Segoe UI", 11, "bold"),
                        padding=8)
        style.map("TButton",
                  background=[('active', '#22223b')])
        style.configure("TEntry",
                        fieldbackground="#2a2a40",
                        foreground="#f0f0f0",
                        font=("Segoe UI", 11),
                        padding=5)
    
    def _create_widgets(self):
        """Создание всех виджетов"""
        pad_opts = {'padx': 15, 'pady': 10}
        
        # Заголовок
        ttk.Label(
            self.root,
            text="Загрузчик отзывов Steam",
            font=("Segoe UI", 18, "bold"),
            foreground="#f2e9e4",
            background="#1e1e2f"
        ).pack(pady=(15, 5))
        
        # --- Строка AppID ---
        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=(10, 0), fill="x", padx=15)
        
        ttk.Label(input_frame, text="AppID или ссылка:").grid(
            row=0, column=0, sticky="w", **pad_opts
        )
        
        self.appid_entry = self._create_entry(input_frame)
        self.appid_entry.grid(row=0, column=1, sticky="w", padx=(0, 5))
        
        self.check_button = ttk.Button(
            input_frame,
            text="Проверить",
            command=self.check_reviews_count
        )
        self.check_button.grid(row=0, column=2, padx=10)
        
        # Информация о количестве отзывов
        self.available_label = ttk.Label(
            self.root,
            text="Всего отзывов: не проверено",
            font=("Segoe UI", 10),
            foreground="#a7a9be",
            background="#1e1e2f"
        )
        self.available_label.pack(anchor="w", padx=25, pady=(3, 10))
        
        # --- Строка количества отзывов ---
        count_frame = ttk.Frame(self.root)
        count_frame.pack(fill="x", padx=15)
        
        ttk.Label(count_frame, text="Количество выводимых отзывов:").grid(
            row=0, column=0, sticky="w", **pad_opts
        )
        
        self.num_entry = self._create_entry(count_frame)
        self.num_entry.grid(row=0, column=1, sticky="w")
        
        # --- Прогресс-бар ---
        self.progress_var = tk.IntVar()
        ttk.Progressbar(
            self.root,
            maximum=100,
            variable=self.progress_var,
            length=500
        ).pack(pady=(20, 10))
        
        # --- Статус ---
        self.status_label = ttk.Label(
            self.root,
            text="Готов к запуску",
            font=("Segoe UI", 10),
            foreground="#a7a9be",
            background="#1e1e2f"
        )
        self.status_label.pack()
        
        # --- Кнопка запуска ---
        self.start_button = ttk.Button(
            self.root,
            text="Начать загрузку",
            command=self.start_download
        )
        self.start_button.pack(pady=20, ipadx=10, ipady=5)
    
    def _create_entry(self, parent):
        """Создает стилизованное поле ввода"""
        return tk.Entry(
            parent,
            width=30,
            bg="#2a2a40",
            fg="#f0f0f0",
            font=("Segoe UI", 11),
            insertbackground="white",
            relief="flat"
        )
    
    def _setup_bindings(self):
        """Настройка привязок клавиш и меню"""
        # Контекстное меню
        self.context_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg="#2a2a40",
            fg="#f0f0f0"
        )
        self.context_menu.add_command(label="Вставить", command=self._paste)
        self.context_menu.add_command(label="Копировать", command=self._copy)
        self.context_menu.add_command(label="Вырезать", command=self._cut)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Очистить", command=self._clear)
        
        # Привязка к полям
        for entry in [self.appid_entry, self.num_entry]:
            entry.bind("<Button-3>", self._show_context_menu)
            entry.bind('<Control-v>', self._paste_via_ctrl)
            entry.bind('<Control-V>', self._paste_via_ctrl)
        
        self.appid_entry.focus_set()
    
    def _show_context_menu(self, event):
        """Показывает контекстное меню"""
        self.current_entry = event.widget
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def _paste(self):
        """Вставка из буфера обмена"""
        if self.current_entry:
            try:
                text = self.root.clipboard_get()
                self.current_entry.insert(tk.INSERT, text)
                self._auto_parse_appid()
            except:
                pass
    
    def _paste_via_ctrl(self, event):
        """Вставка через Ctrl+V"""
        try:
            text = self.root.clipboard_get()
            event.widget.insert(tk.INSERT, text)
            self._auto_parse_appid()
            return "break"
        except:
            return "break"
    
    def _copy(self):
        """Копирование в буфер обмена"""
        if self.current_entry:
            try:
                text = self.current_entry.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
            except:
                pass
    
    def _cut(self):
        """Вырезание в буфер обмена"""
        if self.current_entry:
            try:
                text = self.current_entry.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.current_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except:
                pass
    
    def _clear(self):
        """Очистка поля"""
        if self.current_entry:
            self.current_entry.delete(0, tk.END)
    
    def _auto_parse_appid(self):
        """Автоматическое извлечение AppID из ссылки"""
        text = self.appid_entry.get().strip()
        appid = self._extract_appid(text)
        if appid:
            self.appid_entry.delete(0, tk.END)
            self.appid_entry.insert(0, appid)
            self._update_status(f"✅ Найден AppID: {appid}", "#90be6d")
    
    def _extract_appid(self, text):
        """Извлекает AppID из текста"""
        if text.isdigit():
            return text
        
        patterns = [
            r'store\.steampowered\.com/app/(\d+)',
            r'steamcommunity\.com/app/(\d+)',
            r'steam\.com/app/(\d+)',
            r'app/(\d+)',
            r'/(\d+)/',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _get_appid(self):
        """Получает AppID из поля с авто-извлечением"""
        text = self.appid_entry.get().strip()
        if not text.isdigit():
            extracted = self._extract_appid(text)
            if extracted:
                self.appid_entry.delete(0, tk.END)
                self.appid_entry.insert(0, extracted)
                return extracted
            return None
        return text
    
    def _update_status(self, text, color="#e0e0e0"):
        """Обновляет текст статуса"""
        self.status_label.config(text=text, foreground=color)
    
    def update_progress(self, downloaded, total):
        """Обновляет прогресс-бар"""
        percent = int(downloaded / total * 100)
        self.progress_var.set(percent)
        self._update_status(f"Загружено отзывов: {downloaded} из {total}")
    
    def check_reviews_count(self):
        """Проверяет количество доступных отзывов и получает название игры"""
        appid = self._get_appid()
        if not appid:
            messagebox.showerror("Ошибка", "Введите корректный числовой AppID или ссылку на игру")
            return
        
        self.available_label.config(text="Проверка...", foreground="#f2cc8f")
        self.check_button.config(state="disabled")
        
        def run():
            try:
                # 👇 Получаем название игры
                self.game_name = asyncio.run(self.downloader.fetch_game_name(appid))
                
                # Получаем количество отзывов
                count = asyncio.run(self.downloader.fetch_total_reviews(appid))
                self.available_reviews = count
                
                # Обновляем интерфейс
                name_text = f" ({self.game_name})" if self.game_name else ""
                self.root.after(0, lambda: self.available_label.config(
                    text=f"Всего доступно отзывов: {count}{name_text}", foreground="#90be6d"))
                self._update_status(f"✅ Найдено {count} отзывов" + (f" для {self.game_name}" if self.game_name else ""), "#90be6d")
            except Exception as e:
                self.root.after(0, lambda: self.available_label.config(
                    text=f"Ошибка проверки: {e}", foreground="#f05454"))
            finally:
                self.root.after(0, lambda: self.check_button.config(state="normal"))
        
        threading.Thread(target=run, daemon=True).start()
    
    def start_download(self):
        """Запускает загрузку отзывов"""
        appid = self._get_appid()
        if not appid:
            messagebox.showerror("Ошибка", "Введите корректный числовой AppID или ссылку на игру")
            return
        
        num_str = self.num_entry.get().strip()
        if not num_str.isdigit() or int(num_str) <= 0:
            messagebox.showerror("Ошибка", "Введите положительное число отзывов")
            return
        
        total = int(num_str)
        if self.available_reviews is not None and total > self.available_reviews:
            if not messagebox.askyesno("Подтверждение", 
                f"Запрошено {total} отзывов, а доступно только {self.available_reviews}. Продолжить?"):
                return
        
        self.progress_var.set(0)
        self._update_status("Запуск загрузки...", "#f2cc8f")
        self.start_button.config(state="disabled")
        self.check_button.config(state="disabled")
        
        def run():
            try:
                reviews = asyncio.run(
                    self.downloader.download_reviews(
                        appid, total,
                        progress_callback=self.update_progress
                    )
                )
                # 👇 Передаем название игры для имени файла
                filename = self.downloader.save_to_excel(reviews, appid, self.game_name)
                self._update_status(f"✅ Загрузка завершена! Файл: {filename}", "#90be6d")
            except Exception as e:
                self._update_status(f"❌ Ошибка: {e}", "#f05454")
            finally:
                self.root.after(0, lambda: self.start_button.config(state="normal"))
                self.root.after(0, lambda: self.check_button.config(state="normal"))
        
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = SteamReviewsApp(root)
    root.mainloop()