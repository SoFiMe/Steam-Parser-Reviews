import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
from steam_logic import SteamReviewsDownloader

class SteamReviewsApp:
    def __init__(self, root):
        self.root = root
        root.title("Steam Reviews Downloader")
        root.geometry("590x360")
        root.resizable(False, False)
        root.configure(bg="#1e1e2f")
        
        # Создаем объект логики
        self.downloader = SteamReviewsDownloader()
        self.total_reviews = 0
        self.available_reviews = None
        
        # Стили
        style = ttk.Style(root)
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
        
        pad_opts = {'padx': 15, 'pady': 10}
        
        # Заголовок
        title_lbl = ttk.Label(root, text="Загрузчик отзывов Steam", 
                             font=("Segoe UI", 18, "bold"), 
                             foreground="#f2e9e4", background="#1e1e2f")
        title_lbl.pack(pady=(15,5))
        
        # AppID с подсказкой
        input_frame = ttk.Frame(root)
        input_frame.pack(pady=(10, 0), fill="x", padx=15)
        
        ttk.Label(input_frame, text="AppID или ссылка:").grid(row=0, column=0, sticky="w", **pad_opts)
        
        # Поле ввода
        self.appid_entry = tk.Entry(
            input_frame, 
            width=30,
            bg="#2a2a40",
            fg="#f0f0f0",
            font=("Segoe UI", 11),
            insertbackground="white",
            relief="flat"
        )
        self.appid_entry.grid(row=0, column=1, sticky="w", padx=(0, 5))
        
        # 👇 КНОПКА "Проверить" - сразу после поля
        self.check_button = ttk.Button(input_frame, text="Проверить", command=self.check_reviews_count)
        self.check_button.grid(row=0, column=2, padx=10)
        
        self.available_label = ttk.Label(root, text="Всего отзывов: не проверено", 
                                        font=("Segoe UI", 10), 
                                        foreground="#a7a9be", background="#1e1e2f")
        self.available_label.pack(anchor="w", padx=25, pady=(3, 10))
        
        # Количество отзывов
        count_frame = ttk.Frame(root)
        count_frame.pack(fill="x", padx=15)
        
        ttk.Label(count_frame, text="Количество выводимых отзывов:").grid(row=0, column=0, sticky="w", **pad_opts)
        
        self.num_entry = tk.Entry(
            count_frame, 
            width=30,
            bg="#2a2a40",
            fg="#f0f0f0",
            font=("Segoe UI", 11),
            insertbackground="white",
            relief="flat"
        )
        self.num_entry.grid(row=0, column=1, sticky="w")
        
        # Progress bar
        self.progress_var = tk.IntVar()
        self.progressbar = ttk.Progressbar(root, maximum=100, variable=self.progress_var, length=500)
        self.progressbar.pack(pady=(20, 10))
        
        # Статус
        self.status_label = ttk.Label(root, text="Готов к запуску", 
                                     font=("Segoe UI", 10), 
                                     foreground="#a7a9be", background="#1e1e2f")
        self.status_label.pack()
        
        # Кнопка запуска
        self.start_button = ttk.Button(root, text="Начать загрузку", command=self.start_download)
        self.start_button.pack(pady=20, ipadx=10, ipady=5)
        
        # 👇 СОЗДАЕМ КОНТЕКСТНОЕ МЕНЮ
        self.create_context_menu()
        
        # 👇 ПРИВЯЗЫВАЕМ КОНТЕКСТНОЕ МЕНЮ К ПОЛЯМ
        self.appid_entry.bind("<Button-3>", self.show_context_menu)
        self.num_entry.bind("<Button-3>", self.show_context_menu)
        
        # 👇 ПРИВЯЗЫВАЕМ CTRL+V ДЛЯ ПОЛЕЙ
        self.appid_entry.bind('<Control-v>', self.paste_via_ctrl_v)
        self.appid_entry.bind('<Control-V>', self.paste_via_ctrl_v)
        self.num_entry.bind('<Control-v>', self.paste_via_ctrl_v)
        self.num_entry.bind('<Control-V>', self.paste_via_ctrl_v)
        
        # Фокус на поле AppID
        self.appid_entry.focus_set()
    
    def create_context_menu(self):
        """Создает контекстное меню для полей ввода"""
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#2a2a40", fg="#f0f0f0")
        self.context_menu.add_command(label="Вставить", command=self.paste_from_clipboard)
        self.context_menu.add_command(label="Копировать", command=self.copy_from_entry)
        self.context_menu.add_command(label="Вырезать", command=self.cut_from_entry)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Очистить", command=self.clear_entry)
        
        # Храним ссылку на текущее поле
        self.current_entry = None
    
    def show_context_menu(self, event):
        """Показывает контекстное меню"""
        self.current_entry = event.widget
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def paste_from_clipboard(self):
        """Вставляет текст из буфера обмена в текущее поле"""
        if self.current_entry:
            try:
                clipboard_text = self.root.clipboard_get()
                self.current_entry.insert(tk.INSERT, clipboard_text)
                self.auto_parse_appid()
            except:
                pass
    
    def paste_via_ctrl_v(self, event):
        """Вставка через Ctrl+V"""
        try:
            clipboard_text = self.root.clipboard_get()
            event.widget.insert(tk.INSERT, clipboard_text)
            self.auto_parse_appid()
            return "break"
        except:
            return "break"
    
    def copy_from_entry(self):
        """Копирует выделенный текст из текущего поля"""
        if self.current_entry:
            try:
                selected = self.current_entry.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
            except:
                pass
    
    def cut_from_entry(self):
        """Вырезает выделенный текст из текущего поля"""
        if self.current_entry:
            try:
                selected = self.current_entry.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                self.current_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except:
                pass
    
    def clear_entry(self):
        """Очищает текущее поле"""
        if self.current_entry:
            self.current_entry.delete(0, tk.END)
    
    def auto_parse_appid(self):
        """Автоматически извлекает AppID при вставке"""
        text = self.appid_entry.get().strip()
        appid = self.extract_appid(text)
        if appid:
            self.appid_entry.delete(0, tk.END)
            self.appid_entry.insert(0, appid)
            self.status_label.config(text=f"✅ Найден AppID: {appid}", foreground="#90be6d")
    
    def extract_appid(self, text):
        """Извлекает AppID из текста (ссылки или просто числа)"""
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
    
    def update_progress(self, downloaded, total):
        """Обновляет прогресс-бар"""
        percent = int(downloaded / total * 100)
        self.progress_var.set(percent)
        self.status_label.config(text=f"Загружено отзывов: {downloaded} из {total}", 
                                foreground="#e0e0e0")
    
    def check_reviews_count(self):
        """Проверяет количество доступных отзывов"""
        appid = self.appid_entry.get().strip()
        
        if not appid.isdigit():
            extracted = self.extract_appid(appid)
            if extracted:
                appid = extracted
                self.appid_entry.delete(0, tk.END)
                self.appid_entry.insert(0, appid)
            else:
                messagebox.showerror("Ошибка", "Введите корректный числовой AppID или ссылку на игру")
                return
        
        self.available_label.config(text="Проверка...", foreground="#f2cc8f")
        self.check_button.config(state="disabled")
        
        def run_check():
            try:
                count = asyncio.run(self.downloader.fetch_total_reviews(appid))
                self.available_reviews = count
                self.root.after(0, lambda: self.available_label.config(
                    text=f"Всего доступно отзывов: {count}", foreground="#90be6d"))
                self.root.after(0, lambda: self.status_label.config(
                    text=f"✅ Найдено {count} отзывов", foreground="#90be6d"))
            except Exception as e:
                self.root.after(0, lambda: self.available_label.config(
                    text=f"Ошибка проверки: {e}", foreground="#f05454"))
            finally:
                self.root.after(0, lambda: self.check_button.config(state="normal"))
        
        threading.Thread(target=run_check, daemon=True).start()
    
    def start_download(self):
        """Запускает загрузку отзывов"""
        appid = self.appid_entry.get().strip()
        num_str = self.num_entry.get().strip()
        
        if not appid.isdigit():
            extracted = self.extract_appid(appid)
            if extracted:
                appid = extracted
                self.appid_entry.delete(0, tk.END)
                self.appid_entry.insert(0, appid)
            else:
                messagebox.showerror("Ошибка", "Введите корректный числовой AppID или ссылку на игру")
                return
        
        if not appid.isdigit():
            messagebox.showerror("Ошибка", "Введите корректный числовой AppID")
            return
        if not num_str.isdigit() or int(num_str) <= 0:
            messagebox.showerror("Ошибка", "Введите положительное число отзывов")
            return
        if self.available_reviews is not None and int(num_str) > self.available_reviews:
            if not messagebox.askyesno("Подтверждение", 
                f"Запрошено {num_str} отзывов, а доступно только {self.available_reviews}. Продолжить?"):
                return
        
        total = int(num_str)
        self.progress_var.set(0)
        self.status_label.config(text="Запуск загрузки...", foreground="#f2cc8f")
        self.start_button.config(state="disabled")
        self.check_button.config(state="disabled")
        
        def run_download():
            try:
                reviews = asyncio.run(
                    self.downloader.download_reviews(
                        appid, total, 
                        progress_callback=self.update_progress
                    )
                )
                filename = self.downloader.save_to_excel(reviews, appid)
                self.root.after(0, lambda: self.status_label.config(
                    text=f"✅ Загрузка завершена! Файл: {filename}", 
                    foreground="#90be6d"))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"❌ Ошибка: {e}", foreground="#f05454"))
            finally:
                self.root.after(0, lambda: self.start_button.config(state="normal"))
                self.root.after(0, lambda: self.check_button.config(state="normal"))
        
        threading.Thread(target=run_download, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SteamReviewsApp(root)
    root.mainloop()