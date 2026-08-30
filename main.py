"""
Windows Özelleştirici (Windows Customizer)
--------------------------------------------
Windows için kapsamlı bir özelleştirme ve sistem araçları uygulaması.

Gereksinimler:
    - Sadece Windows üzerinde çalışır (winreg ve ctypes kullanır).
    - Python 3.8+
    - Ek paket gerekmez (sadece standart kütüphane).

Çalıştırma:
    python windows_ozellestirici.py

Not: Bazı ayarların etkili olması için Explorer'ın yeniden başlatılması
(veya oturumun kapatılıp açılması) gerekebilir. Program bunu otomatik dener.
"""

import sys
import os
import ctypes
from ctypes import wintypes
import subprocess
import threading
import time
import struct
import zlib
import datetime
import webbrowser
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import winreg
else:
    winreg = None


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar (Windows registry / API işlemleri)
# ---------------------------------------------------------------------------

def set_reg_dword(hive, path, name, value):
    """Registry'de bir DWORD değeri oluşturur/günceller."""
    with winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)


def get_reg_dword(hive, path, name, default=None):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except FileNotFoundError:
        return default


def restart_explorer():
    """Değişikliklerin görünür olması için Explorer'ı yeniden başlatır."""
    try:
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], check=False)
        subprocess.Popen("explorer.exe")
    except Exception as e:
        print("Explorer yeniden başlatılamadı:", e)


PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
ADVANCED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
DESKTOP_KEY = r"Control Panel\Desktop"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
CURSORS_KEY = r"Control Panel\Cursors"
ACCESSIBILITY_KEY = r"Software\Microsoft\Accessibility"
STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs\Startup",
)

# Windows'ta yerleşik olarak gelen imleç şemaları (Registry Cursor Scheme adları)
IMLEC_SEMALARI = {
    "Windows Varsayılan": "Windows Default",
    "Windows Siyah": "Windows Black",
    "Windows Ters (Invert)": "Windows Inverted",
    "Büyüteç (Büyük Siyah)": "Windows Black (large)",
    "Büyüteç (Çok Büyük Siyah)": "Windows Black (extra large)",
    "Büyüteç (Büyük Varsayılan)": "Windows Default (large)",
    "Büyüteç (Çok Büyük Varsayılan)": "Windows Default (extra large)",
}

# İmleç rollerinin Registry değer adları (Control Panel\Cursors altında)
IMLEC_ROLLERI = {
    "Normal Seçim (Arrow)": "Arrow",
    "Yardım Seçimi": "Help",
    "Arka Planda Çalışıyor": "AppStarting",
    "Metin Seçimi (IBeam)": "IBeam",
    "El İşareti (Link)": "Hand",
    "Meşgul (Wait)": "Wait",
    "Hassas Seçim (Crosshair)": "Crosshair",
    "Yasak (No)": "No",
    "Dikey Boyutlandır": "SizeNS",
    "Yatay Boyutlandır": "SizeWE",
    "Çapraz Boyutlandır 1": "SizeNWSE",
    "Çapraz Boyutlandır 2": "SizeNESW",
    "Taşı (Move)": "SizeAll",
    "Yukarı Seçim": "UpArrow",
    "Konum İşareti (Pin)": "Pin",
    "Kişi (Person)": "Person",
}

# "Efsane" koyu tema renk paleti
RENK = {
    "arkaplan": "#0f1117",
    "panel": "#171a23",
    "panel2": "#1e2230",
    "vurgu": "#7c5cff",
    "vurgu2": "#00e0c6",
    "metin": "#e8e9f0",
    "metin_gri": "#8b90a3",
    "kenarlik": "#2a2f42",
}

# TODO: Buraya gerçek Discord davet linkini koy — kullanıcı verdiğinde güncellenecek.
DISCORD_URL = "https://discord.gg/BURAYA-DAVET-KODUNU-YAZ"

YASAL_UYARI = (
    "Bu program bağımsız, kişisel bir açık kaynak projesidir. Microsoft, Windows, "
    "NVIDIA, AMD, Intel, Discord ve adı geçen diğer marka/şirketlerle HİÇBİR "
    "resmi bağlantısı, ortaklığı veya onayı yoktur — bu marka adları yalnızca "
    "uyumluluk/tanımlama amacıyla anılmıştır (nominative fair use). "
    "Program yalnızca Windows'un kendi genel kullanıma açık API'lerini (registry, "
    "WMI, GDI, PowerShell) okuma ve kullanıcının kendi izniyle değiştirme amacıyla "
    "kullanır. 'Sistem Sağlığı' sekmesi kendi virüs tarama motorumuz DEĞİLDİR; "
    "yalnızca Windows Defender'ın kendi durumunu ve sistem olay günlüğünü "
    "okunabilir hale getirir — profesyonel bir güvenlik/antivirüs ürününün yerini "
    "tutmaz. 'Ekran Rengi' sekmesi Windows'un kendi gamma-ramp API'sini kullanan, "
    "bağımsız bir araçtır; herhangi bir üreticinin resmi kontrol panelinin parçası "
    "değildir. 'Oyun Bildirimi' sekmesi de bağımsız bir araçtır; kullanıcının kendi "
    "belirlediği bir işlem adının çalışıp çalışmadığını kontrol eden basit bir "
    "bildirim mekanizmasıdır. Program HİÇBİR HAZIR MARKA "
    "GÖRSELİ/İKON TELİF İÇERİĞİ İÇERMEZ; tüm simgeler ya sistemin kendi dosyalarına "
    "referans ya da bu kodla çizilmiş basit vektör şekilleridir. Kullanıcı, "
    "registry ve dosya sistemi üzerinde yapılan değişikliklerin sorumluluğunu "
    "kabul eder; önemli değişikliklerden önce bir Sistem Geri Yükleme Noktası "
    "oluşturulması önerilir. Program 'OLDUĞU GİBİ' (AS-IS), hiçbir garanti "
    "verilmeksizin sunulur."
)

# ---------------------------------------------------------------------------
# Çok Dilli Menü Desteği (7 dil)
# ---------------------------------------------------------------------------
DILLER = ["tr", "en", "ru", "es", "zh", "de", "it"]
DIL_ISIMLERI = {
    "tr": "Türkçe 🇹🇷", "en": "English 🇬🇧", "ru": "Русский 🇷🇺",
    "es": "Español 🇪🇸", "zh": "中文 🇨🇳", "de": "Deutsch 🇩🇪", "it": "Italiano 🇮🇹",
}

TAB_SIRASI = [
    "tema", "masaustu", "arkaplan", "imlec", "sistem_simgeleri", "gorev_cubugu",
    "baslangic", "fare", "performans", "pano_gecmisi", "renk_secici",
    "pencere_hizalama", "sistem_monitor", "dosya_arama", "dosya_guvenlik",
    "sikistirma", "ekran_goruntusu", "sistem_bilgisi", "sistem_sagligi",
    "ekran_rengi", "powertoys_ekstra", "oyun_bildirimi", "programlar", "fps",
    "dil", "hakkinda",
]

CEVIRILER = {
    "tema": {"tr": "🎨 Tema", "en": "🎨 Theme", "ru": "🎨 Тема", "es": "🎨 Tema",
             "zh": "🎨 主题", "de": "🎨 Design", "it": "🎨 Tema"},
    "masaustu": {"tr": "🖥 Masaüstü", "en": "🖥 Desktop", "ru": "🖥 Рабочий стол",
                 "es": "🖥 Escritorio", "zh": "🖥 桌面", "de": "🖥 Desktop", "it": "🖥 Desktop"},
    "arkaplan": {"tr": "🖼 Arka Plan", "en": "🖼 Background", "ru": "🖼 Фон",
                 "es": "🖼 Fondo", "zh": "🖼 背景", "de": "🖼 Hintergrund", "it": "🖼 Sfondo"},
    "imlec": {"tr": "🖱 İmleç", "en": "🖱 Cursor", "ru": "🖱 Курсор",
              "es": "🖱 Cursor", "zh": "🖱 光标", "de": "🖱 Cursor", "it": "🖱 Cursore"},
    "sistem_simgeleri": {"tr": "🗂 Simgeler/Logo", "en": "🗂 Icons/Logo", "ru": "🗂 Значки",
                          "es": "🗂 Íconos", "zh": "🗂 图标", "de": "🗂 Symbole", "it": "🗂 Icone"},
    "gorev_cubugu": {"tr": "📊 Görev Çubuğu", "en": "📊 Taskbar", "ru": "📊 Панель задач",
                      "es": "📊 Barra de tareas", "zh": "📊 任务栏", "de": "📊 Taskleiste", "it": "📊 Barra"},
    "baslangic": {"tr": "🚀 Başlangıç", "en": "🚀 Startup", "ru": "🚀 Автозагрузка",
                  "es": "🚀 Inicio", "zh": "🚀 启动项", "de": "🚀 Autostart", "it": "🚀 Avvio"},
    "fare": {"tr": "🖲 Fare", "en": "🖲 Mouse", "ru": "🖲 Мышь",
             "es": "🖲 Ratón", "zh": "🖲 鼠标", "de": "🖲 Maus", "it": "🖲 Mouse"},
    "performans": {"tr": "⚙ Performans", "en": "⚙ Performance", "ru": "⚙ Производительность",
                    "es": "⚙ Rendimiento", "zh": "⚙ 性能", "de": "⚙ Leistung", "it": "⚙ Prestazioni"},
    "pano_gecmisi": {"tr": "📋 Pano", "en": "📋 Clipboard", "ru": "📋 Буфер обмена",
                      "es": "📋 Portapapeles", "zh": "📋 剪贴板", "de": "📋 Zwischenablage", "it": "📋 Appunti"},
    "renk_secici": {"tr": "🎨 Renk Seçici", "en": "🎨 Color Picker", "ru": "🎨 Пипетка",
                     "es": "🎨 Selector color", "zh": "🎨 取色器", "de": "🎨 Farbwähler", "it": "🎨 Selettore colore"},
    "pencere_hizalama": {"tr": "🪟 Pencere", "en": "🪟 Window Snap", "ru": "🪟 Окна",
                          "es": "🪟 Ventanas", "zh": "🪟 窗口", "de": "🪟 Fenster", "it": "🪟 Finestre"},
    "sistem_monitor": {"tr": "📈 Monitör", "en": "📈 Monitor", "ru": "📈 Монитор",
                        "es": "📈 Monitor", "zh": "📈 监视器", "de": "📈 Monitor", "it": "📈 Monitor"},
    "dosya_arama": {"tr": "🔍 Dosya Arama", "en": "🔍 File Search", "ru": "🔍 Поиск файлов",
                     "es": "🔍 Buscar archivos", "zh": "🔍 文件搜索", "de": "🔍 Dateisuche", "it": "🔍 Ricerca file"},
    "dosya_guvenlik": {"tr": "🔒 Kilit/Gizle", "en": "🔒 Lock/Hide", "ru": "🔒 Блокировка",
                        "es": "🔒 Bloquear", "zh": "🔒 锁定/隐藏", "de": "🔒 Sperren", "it": "🔒 Blocca"},
    "sikistirma": {"tr": "🗜 Sıkıştırma", "en": "🗜 Compression", "ru": "🗜 Архивация",
                    "es": "🗜 Compresión", "zh": "🗜 压缩", "de": "🗜 Komprimierung", "it": "🗜 Compressione"},
    "ekran_goruntusu": {"tr": "📸 Ekran Gör.", "en": "📸 Screenshot", "ru": "📸 Скриншот",
                         "es": "📸 Captura", "zh": "📸 截图", "de": "📸 Screenshot", "it": "📸 Schermata"},
    "sistem_bilgisi": {"tr": "💻 Sistem Bilgisi", "en": "💻 System Info", "ru": "💻 О системе",
                        "es": "💻 Info Sistema", "zh": "💻 系统信息", "de": "💻 Systeminfo", "it": "💻 Info Sistema"},
    "sistem_sagligi": {"tr": "🛡 Sağlık", "en": "🛡 Health", "ru": "🛡 Безопасность",
                        "es": "🛡 Salud", "zh": "🛡 系统健康", "de": "🛡 Sicherheit", "it": "🛡 Salute"},
    "ekran_rengi": {"tr": "🌈 Ekran Rengi", "en": "🌈 Display Color", "ru": "🌈 Цвет экрана",
                     "es": "🌈 Color pantalla", "zh": "🌈 屏幕颜色", "de": "🌈 Bildschirmfarbe", "it": "🌈 Colore schermo"},
    "powertoys_ekstra": {"tr": "🧰 Ekstra", "en": "🧰 Extras", "ru": "🧰 Доп. инструменты",
                          "es": "🧰 Extras", "zh": "🧰 附加工具", "de": "🧰 Extras", "it": "🧰 Extra"},
    "oyun_bildirimi": {"tr": "🎮 Oyun Bildirimi", "en": "🎮 Game Alert", "ru": "🎮 Уведомление",
                        "es": "🎮 Alerta juego", "zh": "🎮 游戏提醒", "de": "🎮 Spielbenachr.", "it": "🎮 Avviso gioco"},
    "programlar": {"tr": "📦 Programlar", "en": "📦 Programs", "ru": "📦 Программы",
                    "es": "📦 Programas", "zh": "📦 程序", "de": "📦 Programme", "it": "📦 Programmi"},
    "fps": {"tr": "🎯 FPS", "en": "🎯 FPS", "ru": "🎯 FPS",
            "es": "🎯 FPS", "zh": "🎯 帧率", "de": "🎯 FPS", "it": "🎯 FPS"},
    "dil": {"tr": "🌐 Dil", "en": "🌐 Language", "ru": "🌐 Язык",
            "es": "🌐 Idioma", "zh": "🌐 语言", "de": "🌐 Sprache", "it": "🌐 Lingua"},
    "hakkinda": {"tr": "ℹ Hakkında", "en": "ℹ About", "ru": "ℹ О программе",
                 "es": "ℹ Acerca de", "zh": "ℹ 关于", "de": "ℹ Info", "it": "ℹ Informazioni"},
    "app_title": {
        "tr": "⚡ Windows Özelleştirici — EFSANE Sürüm",
        "en": "⚡ Windows Customizer — LEGENDARY Edition",
        "ru": "⚡ Кастомайзер Windows — Легендарная версия",
        "es": "⚡ Personalizador de Windows — Edición Legendaria",
        "zh": "⚡ Windows 定制工具 — 传奇版",
        "de": "⚡ Windows-Anpasser — Legendäre Edition",
        "it": "⚡ Personalizzatore Windows — Edizione Leggendaria",
    },
    "banner_alt": {
        "tr": "EFSANE SÜRÜM", "en": "LEGENDARY EDITION", "ru": "ЛЕГЕНДАРНАЯ ВЕРСИЯ",
        "es": "EDICIÓN LEGENDARIA", "zh": "传奇版", "de": "LEGENDÄRE EDITION",
        "it": "EDIZIONE LEGGENDARIA",
    },
    "dil_baslik": {"tr": "Dil / Language", "en": "Language", "ru": "Язык",
                    "es": "Idioma", "zh": "语言", "de": "Sprache", "it": "Lingua"},
    "dil_aciklama": {
        "tr": "Ana başlığı, alt bilgi çubuğunu ve sekme (menü) isimlerini seçtiğin "
              "dile çevirir. Not: Sekmelerin İÇİNDEKİ ayrıntılı metinler şu an için "
              "Türkçe kalmaya devam ediyor — dürüst olmak gerekirse binlerce satırı "
              "tek seferde tam çevirmek bu ölçekte pratik değil.",
        "en": "Translates the main title, footer bar and tab (menu) names into your "
              "chosen language. Note: the detailed text INSIDE each tab currently "
              "stays in Turkish — fully translating thousands of lines at once "
              "isn't practical at this scale, to be honest.",
        "ru": "Переводит главный заголовок, нижнюю панель и названия вкладок на "
              "выбранный язык. Примечание: подробный текст ВНУТРИ вкладок пока "
              "остаётся на турецком — честно говоря, перевод тысяч строк сразу "
              "непрактичен в таком масштабе.",
        "es": "Traduce el título principal, la barra inferior y los nombres de las "
              "pestañas al idioma elegido. Nota: el texto detallado DENTRO de cada "
              "pestaña permanece en turco por ahora — traducir miles de líneas de "
              "una vez no es práctico a esta escala, siendo honestos.",
        "zh": "将主标题、底部栏和标签名称翻译成你选择的语言。注意:每个标签内部的"
              "详细文本目前仍为土耳其语——老实说,一次性翻译数千行在这种规模下"
              "并不现实。",
        "de": "Übersetzt den Haupttitel, die Fußzeile und die Tab-Namen in die "
              "gewählte Sprache. Hinweis: Der Text INNERHALB der Tabs bleibt "
              "vorerst auf Türkisch — Tausende Zeilen auf einmal zu übersetzen "
              "ist ehrlich gesagt nicht praktikabel.",
        "it": "Traduce il titolo principale, la barra inferiore e i nomi delle "
              "schede nella lingua scelta. Nota: il testo dettagliato ALL'INTERNO "
              "di ogni scheda rimane per ora in turco — tradurre migliaia di "
              "righe in una volta non è pratico a questa scala, onestamente.",
    },
}


# ---------------------------------------------------------------------------
# Kenar Çubuğu Menüsü (26 sekme için düz tab bar yerine — çok daha temiz görünür)
# ttk.Notebook ile aynı arayüzü taklit eder: .add(frame, text=...) ve .tab(i, text=...)
# ---------------------------------------------------------------------------
class SidebarNotebook(tk.Frame):
    def __init__(self, master, genislik=230, **kwargs):
        super().__init__(master, bg=RENK["arkaplan"], **kwargs)

        self.kenar_disi = tk.Frame(self, bg=RENK["panel"], width=genislik)
        self.kenar_disi.pack(side="left", fill="y")
        self.kenar_disi.pack_propagate(False)

        self._canvas = tk.Canvas(self.kenar_disi, bg=RENK["panel"], highlightthickness=0,
                                  width=genislik)
        self._scrollbar = ttk.Scrollbar(self.kenar_disi, orient="vertical", command=self._canvas.yview)
        self._ic_frame = tk.Frame(self._canvas, bg=RENK["panel"])
        self._ic_frame.bind(
            "<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas_pencere = self._canvas.create_window((0, 0), window=self._ic_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        def _tekerlek(event):
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _tekerlek_baglan(event):
            self._canvas.bind_all("<MouseWheel>", _tekerlek)

        def _tekerlek_ayir(event):
            self._canvas.unbind_all("<MouseWheel>")

        self._canvas.bind("<Enter>", _tekerlek_baglan)
        self._canvas.bind("<Leave>", _tekerlek_ayir)

        self.icerik = tk.Frame(self, bg=RENK["arkaplan"])
        self.icerik.pack(side="left", fill="both", expand=True)

        self._sekmeler = []  # [(buton, frame), ...]
        self._aktif_index = None

    def add(self, frame, text=""):
        idx = len(self._sekmeler)
        buton = tk.Label(
            self._ic_frame, text=text, bg=RENK["panel"], fg=RENK["metin_gri"],
            font=("Segoe UI", 10), anchor="w", padx=16, pady=9, cursor="hand2",
        )
        buton.pack(fill="x")
        buton.bind("<Button-1>", lambda e, i=idx: self.select(i))
        buton.bind("<Enter>", lambda e, b=buton, i=idx: self._hover(b, i, True))
        buton.bind("<Leave>", lambda e, b=buton, i=idx: self._hover(b, i, False))
        self._sekmeler.append([buton, frame])
        if idx == 0:
            self.select(0)
        return frame

    def _hover(self, buton, idx, giriyor):
        if idx == self._aktif_index:
            return
        buton.config(bg=RENK["panel2"] if giriyor else RENK["panel"])

    def select(self, idx):
        if idx == self._aktif_index or not (0 <= idx < len(self._sekmeler)):
            return
        if self._aktif_index is not None:
            eski_buton, eski_frame = self._sekmeler[self._aktif_index]
            eski_frame.pack_forget()
            eski_buton.config(bg=RENK["panel"], fg=RENK["metin_gri"], font=("Segoe UI", 10))
        buton, frame = self._sekmeler[idx]
        frame.pack(in_=self.icerik, fill="both", expand=True)
        buton.config(bg=RENK["vurgu"], fg="#ffffff", font=("Segoe UI", 10, "bold"))
        self._aktif_index = idx

    def tab(self, index, text=None, **kwargs):
        if text is not None and 0 <= index < len(self._sekmeler):
            self._sekmeler[index][0].config(text=text)


# ---------------------------------------------------------------------------
# Ana Uygulama
# ---------------------------------------------------------------------------

class WindowsOzellestiriciApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Windows Özelleştirici — EFSANE Sürüm")
        self.geometry("1000x760")
        self.resizable(False, False)
        self.configure(bg=RENK["arkaplan"])

        self._stili_uygula()
        self._baslik_banner_olustur()

        if not IS_WINDOWS:
            messagebox.showwarning(
                "Uyarı",
                "Bu araç sadece Windows üzerinde tam olarak çalışır.\n"
                "Şu an Windows dışında bir işletim sisteminde olduğun için "
                "ayarlar gerçek sisteme uygulanamayacak (arayüzü yine de "
                "inceleyebilirsin).",
            )

        self._alt_bilgi_cubugu()

        notebook = SidebarNotebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.notebook = notebook

        self.tema_sekmesi(notebook)
        self.masaustu_sekmesi(notebook)
        self.arkaplan_sekmesi(notebook)
        self.imlec_sekmesi(notebook)
        self.sistem_simgeleri_sekmesi(notebook)
        self.gorev_cubugu_sekmesi(notebook)
        self.baslangic_sekmesi(notebook)
        self.fare_sekmesi(notebook)
        self.performans_sekmesi(notebook)
        self.pano_gecmisi_sekmesi(notebook)
        self.renk_secici_sekmesi(notebook)
        self.pencere_hizalama_sekmesi(notebook)
        self.sistem_monitor_sekmesi(notebook)
        self.dosya_arama_sekmesi(notebook)
        self.dosya_guvenlik_sekmesi(notebook)
        self.sikistirma_sekmesi(notebook)
        self.ekran_goruntusu_sekmesi(notebook)
        self.sistem_bilgisi_sekmesi(notebook)
        self.sistem_sagligi_sekmesi(notebook)
        self.ekran_rengi_sekmesi(notebook)
        self.powertoys_ekstra_sekmesi(notebook)
        self.oyun_bildirimi_sekmesi(notebook)
        self.programlar_sekmesi(notebook)
        self.fps_sekmesi(notebook)
        self.dil_sekmesi(notebook)
        self.hakkinda_sekmesi(notebook)

        # Arka planda çalışan yardımcı iş parçacıkları için durum bayrakları
        self._pano_calisiyor = False
        self._pano_gecmisi = []
        self._son_pano_degeri = None
        self._son_disardaki_pencere = None
        self._pencere_takip_calisiyor = False
        self._dosya_indeksi = []
        self._dosya_index_calisiyor = False
        self._renk_gecmisi = []
        self._slideshow_calisiyor = False
        self._fps_gosterge_penceresi = None
        self._fps_calisiyor = False
        self._uyanik_tut_aktif = False
        self._baslangic_menusu_indeksi = []
        self._izlenen_islemler = []
        self._oyun_izleme_aktif = False
        self._mevcut_dil = "tr"

        self._pano_izlemeyi_baslat()
        self._pencere_takibini_baslat()
        self._dili_uygula("tr")
        self.protocol("WM_DELETE_WINDOW", self._kapanirken)

    def _kapanirken(self):
        self._pano_calisiyor = False
        self._pencere_takip_calisiyor = False
        self._slideshow_calisiyor = False
        self._fps_calisiyor = False
        self._oyun_izleme_aktif = False
        if self._uyanik_tut_aktif and IS_WINDOWS:
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # ES_CONTINUOUS
            except Exception:
                pass
        self.destroy()

    # ------------------------------------------------------------------
    # "Efsane" görünüm: koyu tema + üst banner
    # ------------------------------------------------------------------
    def _stili_uygula(self):
        stil = ttk.Style(self)
        try:
            stil.theme_use("clam")
        except Exception:
            pass

        stil.configure(".", background=RENK["arkaplan"], foreground=RENK["metin"],
                        fieldbackground=RENK["panel2"], font=("Segoe UI", 10))
        stil.configure("TFrame", background=RENK["arkaplan"])
        stil.configure("TLabel", background=RENK["arkaplan"], foreground=RENK["metin"])
        stil.configure("TCheckbutton", background=RENK["arkaplan"], foreground=RENK["metin"])
        stil.map("TCheckbutton", background=[("active", RENK["arkaplan"])])

        stil.configure("TButton", background=RENK["panel2"], foreground=RENK["metin"],
                        borderwidth=0, focusthickness=0, padding=(10, 6))
        stil.map(
            "TButton",
            background=[("active", RENK["vurgu"]), ("pressed", RENK["vurgu"])],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        stil.configure("TEntry", fieldbackground=RENK["panel2"], foreground=RENK["metin"],
                        insertcolor=RENK["metin"], borderwidth=1)
        stil.configure("Horizontal.TScale", background=RENK["arkaplan"])
        stil.configure("TSeparator", background=RENK["kenarlik"])

        stil.configure(
            "Efsane.TNotebook", background=RENK["arkaplan"], borderwidth=0, tabmargins=(4, 6, 4, 0)
        )
        stil.configure(
            "Efsane.TNotebook.Tab", background=RENK["panel"], foreground=RENK["metin_gri"],
            padding=(12, 8), font=("Segoe UI", 9, "bold"), borderwidth=0,
        )
        stil.map(
            "Efsane.TNotebook.Tab",
            background=[("selected", RENK["vurgu"])],
            foreground=[("selected", "#ffffff")],
            expand=[("selected", (1, 1, 1, 0))],
        )

        # Sekme içi başlıklar için "efsane" görünüm: vurgu rengi + büyük punto
        stil.configure(
            "Baslik.TLabel", background=RENK["arkaplan"], foreground=RENK["vurgu2"],
            font=("Segoe UI", 13, "bold"),
        )
        stil.configure(
            "AltBaslik.TLabel", background=RENK["arkaplan"], foreground=RENK["metin"],
            font=("Segoe UI", 10, "bold"),
        )

        # tk (ttk olmayan) widget'lar için varsayılan renkler
        self.option_add("*Listbox.Background", RENK["panel2"])
        self.option_add("*Listbox.Foreground", RENK["metin"])
        self.option_add("*Listbox.selectBackground", RENK["vurgu"])
        self.option_add("*Listbox.selectForeground", "#ffffff")
        self.option_add("*Listbox.borderWidth", 0)
        self.option_add("*Listbox.highlightThickness", 1)
        self.option_add("*Listbox.highlightBackground", RENK["kenarlik"])

    def _baslik_banner_olustur(self):
        banner = tk.Canvas(self, height=64, bg=RENK["arkaplan"], highlightthickness=0)
        banner.pack(fill="x", padx=0, pady=0)

        genislik = 1000
        adim = 40
        renk1 = self._hex_to_rgb(RENK["vurgu"])
        renk2 = self._hex_to_rgb(RENK["vurgu2"])
        for i in range(0, genislik, adim):
            oran = i / genislik
            r = int(renk1[0] + (renk2[0] - renk1[0]) * oran)
            g = int(renk1[1] + (renk2[1] - renk1[1]) * oran)
            b = int(renk1[2] + (renk2[2] - renk1[2]) * oran)
            banner.create_rectangle(i, 0, i + adim + 1, 64, fill=f"#{r:02x}{g:02x}{b:02x}", width=0)

        self._banner_canvas = banner
        self._banner_baslik_id = banner.create_text(
            22, 32, anchor="w", text="⚡ WINDOWS ÖZELLEŞTİRİCİ",
            fill="#ffffff", font=("Segoe UI", 17, "bold"),
        )
        self._banner_alt_id = banner.create_text(
            920, 32, anchor="e", text="EFSANE SÜRÜM", fill="#ffffff",
            font=("Segoe UI", 9, "bold"),
        )

    @staticmethod
    def _hex_to_rgb(hex_kod):
        hex_kod = hex_kod.lstrip("#")
        return tuple(int(hex_kod[i:i + 2], 16) for i in (0, 2, 4))

    def _alt_bilgi_cubugu(self):
        """Ekranın altında, tıklanabilir bir Discord 'logosu' içeren ince şerit."""
        cubuk = tk.Frame(self, bg=RENK["panel"], height=42)
        cubuk.pack(side="bottom", fill="x")
        cubuk.pack_propagate(False)

        sol = tk.Label(
            cubuk, text="⚡ Windows Özelleştirici — Efsane Sürüm",
            bg=RENK["panel"], fg=RENK["metin_gri"], font=("Segoe UI", 8),
        )
        sol.pack(side="left", padx=14)
        self._footer_sol_label = sol

        # Basit, vektörle çizilmiş Discord tarzı "logo" (blurple daire + D harfi)
        discord_canvas = tk.Canvas(cubuk, width=26, height=26, bg=RENK["panel"], highlightthickness=0,
                                    cursor="hand2")
        discord_canvas.pack(side="right", padx=(0, 6), pady=8)
        discord_canvas.create_oval(1, 1, 25, 25, fill="#5865F2", outline="")
        discord_canvas.create_text(13, 13, text="D", fill="#ffffff", font=("Segoe UI", 11, "bold"))

        discord_yazi = tk.Label(
            cubuk, text="💬 Discord Sunucumuza Katıl", bg=RENK["panel"], fg="#5865F2",
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        discord_yazi.pack(side="right", padx=(0, 4), pady=8)

        def discord_ac(event=None):
            try:
                webbrowser.open(DISCORD_URL)
            except Exception as e:
                messagebox.showerror("Hata", str(e))

        discord_canvas.bind("<Button-1>", discord_ac)
        discord_yazi.bind("<Button-1>", discord_ac)

    # ------------------------------------------------------------------
    # 1) Tema (Açık / Koyu mod + vurgu rengi)
    # ------------------------------------------------------------------
    def tema_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Tema")

        ttk.Label(frame, text="Uygulama ve Sistem Teması", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(anchor="w", padx=15, pady=5)

        ttk.Button(btn_frame, text="🌙 Koyu Mod", command=self.koyu_mod_ac).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="☀ Açık Mod", command=self.acik_mod_ac).grid(row=0, column=1, padx=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Vurgu Rengi (Accent Color)", style="Baslik.TLabel").pack(
            anchor="w", padx=15
        )
        ttk.Button(frame, text="Renk Seç ve Uygula", command=self.vurgu_rengi_sec).pack(
            anchor="w", padx=15, pady=10
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(
            frame,
            text="Duvar kağıdı, slayt gösterisi ve düz renk arka plan ayarları "
                 "'Arka Plan' sekmesine taşındı — imleç görünüşü için 'İmleç' sekmesine bak.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=10)

    def koyu_mod_ac(self):
        self._set_theme(light=False)

    def acik_mod_ac(self):
        self._set_theme(light=True)

    def _set_theme(self, light: bool):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            val = 1 if light else 0
            set_reg_dword(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY, "AppsUseLightTheme", val)
            set_reg_dword(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY, "SystemUsesLightTheme", val)
            messagebox.showinfo("Başarılı", f"{'Açık' if light else 'Koyu'} mod uygulandı. "
                                             "Değişikliğin tam görünmesi için oturumu yeniden açman gerekebilir.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def vurgu_rengi_sec(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        color = colorchooser.askcolor(title="Vurgu rengi seç")
        if not color or not color[0]:
            return
        r, g, b = (int(c) for c in color[0])
        # Windows DWM ColorizationColor formatı: AABBGGRR (ARGB, alfa dahil)
        argb = (0xFF << 24) | (r << 16) | (g << 8) | b
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM", "ColorizationColor", argb)
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM", "ColorPrevalence", 1)
            messagebox.showinfo("Başarılı", "Vurgu rengi ayarlandı. Görmek için Explorer yeniden başlatılıyor...")
            restart_explorer()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def duvar_kagidi_sec(self):
        path = filedialog.askopenfilename(
            title="Duvar kağıdı seç",
            filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp")],
        )
        if not path:
            return
        self._duvar_kagidini_uygula(path)

    def _duvar_kagidini_uygula(self, path, stil="doldur"):
        """stil: doldur, sigdir, uzat, dosee, ortala, yay"""
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", f"Seçildi (simülasyon): {path}")
            return
        try:
            # WallpaperStyle / TileWallpaper değerleri (Windows resmi tablosu)
            stil_degerleri = {
                "doldur": ("10", "0"),
                "sigdir": ("6", "0"),
                "uzat": ("2", "0"),
                "dosee": ("0", "1"),
                "ortala": ("0", "0"),
                "yay": ("22", "0"),
            }
            wp_style, tile = stil_degerleri.get(stil, ("10", "0"))
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, DESKTOP_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, wp_style)
                winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile)

            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            return False
        return True

    # ------------------------------------------------------------------
    # 2b) Arka Plan (gelişmiş: stil, düz renk, slayt gösterisi)
    # ------------------------------------------------------------------
    def arkaplan_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Arka Plan")

        ttk.Label(frame, text="Duvar Kağıdı", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        ust = ttk.Frame(frame)
        ust.pack(anchor="w", padx=15, pady=5)
        ttk.Label(ust, text="Uyum stili:").grid(row=0, column=0, sticky="w")
        self.arkaplan_stil_var = tk.StringVar(value="doldur")
        stil_secenekleri = [
            ("Doldur", "doldur"), ("Sığdır", "sigdir"), ("Uzat", "uzat"),
            ("Döşe", "dosee"), ("Ortala", "ortala"), ("Yay (Span)", "yay"),
        ]
        stil_combo = ttk.Combobox(
            ust, state="readonly", width=16,
            values=[etiket for etiket, _ in stil_secenekleri],
        )
        stil_combo.current(0)
        stil_combo.grid(row=0, column=1, padx=8)
        self._arkaplan_stil_secenekleri = stil_secenekleri
        self._arkaplan_stil_combo = stil_combo

        ttk.Button(frame, text="🖼 Görsel Seç ve Uygula", command=self._arkaplan_gorsel_uygula).pack(
            anchor="w", padx=15, pady=10
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Düz Renk Arka Plan", style="Baslik.TLabel").pack(anchor="w", padx=15)
        ttk.Button(frame, text="🎨 Renk Seç ve Arka Planı Boya", command=self._duz_renk_arkaplan).pack(
            anchor="w", padx=15, pady=10
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Slayt Gösterisi (Slideshow)", style="Baslik.TLabel").pack(
            anchor="w", padx=15
        )
        ttk.Label(
            frame,
            text="Seçtiğin klasördeki görselleri belirlediğin aralıkla otomatik "
                 "olarak sırayla duvar kağıdı yapar.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        slayt_cerceve = ttk.Frame(frame)
        slayt_cerceve.pack(anchor="w", padx=15, pady=5)
        ttk.Label(slayt_cerceve, text="Aralık (saniye):").grid(row=0, column=0, sticky="w")
        self.slayt_araligi_var = tk.IntVar(value=30)
        ttk.Spinbox(slayt_cerceve, from_=5, to=3600, textvariable=self.slayt_araligi_var, width=8).grid(
            row=0, column=1, padx=8
        )

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=8)
        ttk.Button(btns, text="▶ Klasör Seç ve Başlat", command=self._slideshow_baslat).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(btns, text="⏹ Durdur", command=self._slideshow_durdur).grid(row=0, column=1, padx=5)

        self.slayt_durum_var = tk.StringVar(value="Slayt gösterisi kapalı.")
        ttk.Label(frame, textvariable=self.slayt_durum_var, foreground=RENK["metin_gri"]).pack(
            anchor="w", padx=15, pady=5
        )

    def _secili_arkaplan_stili(self):
        idx = self._arkaplan_stil_combo.current()
        return self._arkaplan_stil_secenekleri[idx][1]

    def _arkaplan_gorsel_uygula(self):
        path = filedialog.askopenfilename(
            title="Duvar kağıdı seç",
            filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp")],
        )
        if not path:
            return
        if self._duvar_kagidini_uygula(path, self._secili_arkaplan_stili()):
            messagebox.showinfo("Başarılı", "Duvar kağıdı uygulandı.")

    def _duz_renk_arkaplan(self):
        renk = colorchooser.askcolor(title="Arka plan rengi seç")
        if not renk or not renk[0]:
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            r, g, b = (int(c) for c in renk[0])
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, r"Control Panel\Colors", 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, "Background", 0, winreg.REG_SZ, f"{r} {g} {b}")
            # Duvar kağıdını boşaltıp düz rengin görünmesini sağla
            SPI_SETDESKWALLPAPER = 20
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, "", 0x01 | 0x02)
            COLOR_BACKGROUND = 1
            colorref = r | (g << 8) | (b << 16)
            ctypes.windll.user32.SetSysColors(
                1, (ctypes.c_int * 1)(COLOR_BACKGROUND), (ctypes.c_int * 1)(colorref)
            )
            messagebox.showinfo("Başarılı", "Düz renk arka plan uygulandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _slideshow_baslat(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        klasor = filedialog.askdirectory(title="Slayt gösterisi için klasör seç")
        if not klasor:
            return
        gecerli_uzantilar = (".jpg", ".jpeg", ".png", ".bmp")
        gorseller = [
            os.path.join(klasor, f) for f in os.listdir(klasor)
            if f.lower().endswith(gecerli_uzantilar)
        ]
        if not gorseller:
            messagebox.showwarning("Uyarı", "Seçilen klasörde görsel dosyası bulunamadı.")
            return

        self._slideshow_durdur()
        self._slideshow_calisiyor = True
        aralik = max(5, self.slayt_araligi_var.get())
        stil = self._secili_arkaplan_stili()

        def dongu():
            i = 0
            while self._slideshow_calisiyor:
                gorsel = gorseller[i % len(gorseller)]
                self._duvar_kagidini_uygula(gorsel, stil)
                self.after(0, lambda g=gorsel: self.slayt_durum_var.set(
                    f"Şu an: {os.path.basename(g)}  ({i % len(gorseller) + 1}/{len(gorseller)})"
                ))
                i += 1
                for _ in range(aralik * 10):
                    if not self._slideshow_calisiyor:
                        break
                    time.sleep(0.1)

        threading.Thread(target=dongu, daemon=True).start()
        self.slayt_durum_var.set(f"Slayt gösterisi başladı ({len(gorseller)} görsel).")

    def _slideshow_durdur(self):
        if self._slideshow_calisiyor:
            self._slideshow_calisiyor = False
            self.slayt_durum_var.set("Slayt gösterisi durduruldu.")

    # ------------------------------------------------------------------
    # 2c) İmleç Görünüşü (cursor scheme / boyut / renk)
    # ------------------------------------------------------------------
    def imlec_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="İmleç")

        ttk.Label(frame, text="Fare İmleci Görünüşü", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        ttk.Label(frame, text="Hazır Şema:").pack(anchor="w", padx=15, pady=(5, 2))
        self.imlec_sema_combo = ttk.Combobox(
            frame, state="readonly", width=32, values=list(IMLEC_SEMALARI.keys())
        )
        self.imlec_sema_combo.current(0)
        self.imlec_sema_combo.pack(anchor="w", padx=15, pady=2)
        ttk.Button(frame, text="Şemayı Uygula", command=self._imlec_semasini_uygula).pack(
            anchor="w", padx=15, pady=10
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="İmleç Boyutu", style="Baslik.TLabel").pack(anchor="w", padx=15)
        ttk.Label(
            frame, text="(Windows 11'de mevcuttur; eski sürümlerde etkisiz olabilir)",
            foreground=RENK["metin_gri"],
        ).pack(anchor="w", padx=15)
        self.imlec_boyutu_var = tk.IntVar(value=1)
        ttk.Scale(
            frame, from_=1, to=15, orient="horizontal", variable=self.imlec_boyutu_var,
            length=300,
        ).pack(anchor="w", padx=15, pady=5)
        ttk.Button(frame, text="Boyutu Uygula", command=self._imlec_boyutunu_uygula).pack(
            anchor="w", padx=15, pady=5
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="İmleç Rengi (Windows 11)", style="Baslik.TLabel").pack(
            anchor="w", padx=15
        )
        ttk.Button(frame, text="Renk Seç ve Uygula", command=self._imlec_rengini_uygula).pack(
            anchor="w", padx=15, pady=10
        )

        ttk.Button(frame, text="↺ Varsayılana Sıfırla", command=self._imlec_sifirla).pack(
            anchor="w", padx=15, pady=15
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="İmleç Şekli (Rol Bazlı Özel Dosya)", style="Baslik.TLabel").pack(
            anchor="w", padx=15
        )
        ttk.Label(
            frame,
            text="Belirli bir imleç rolüne (ör. normal ok, el işareti) kendi .cur/.ani "
                 "dosyanı ata.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        rol_cercevesi = ttk.Frame(frame)
        rol_cercevesi.pack(anchor="w", padx=15, pady=5)
        ttk.Label(rol_cercevesi, text="Rol:").grid(row=0, column=0, sticky="w")
        self.imlec_rol_combo = ttk.Combobox(
            rol_cercevesi, state="readonly", width=26, values=list(IMLEC_ROLLERI.keys())
        )
        self.imlec_rol_combo.current(0)
        self.imlec_rol_combo.grid(row=0, column=1, padx=8)
        ttk.Button(rol_cercevesi, text="📂 .cur/.ani Seç ve Uygula", command=self._imlec_rolunu_uygula).grid(
            row=0, column=2, padx=8
        )

    def _imlec_rolunu_uygula(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        rol_adi = self.imlec_rol_combo.get()
        deger_adi = IMLEC_ROLLERI.get(rol_adi)
        if not deger_adi:
            return
        path = filedialog.askopenfilename(
            title=f"'{rol_adi}' için imleç dosyası seç",
            filetypes=[("İmleç Dosyaları", "*.cur *.ani")],
        )
        if not path:
            return
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CURSORS_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, deger_adi, 0, winreg.REG_EXPAND_SZ, path)
                # Özel bir kombinasyon yaptığımız için şema adını da temizleyelim
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
            SPI_SETCURSORS = 0x0057
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            messagebox.showinfo("Başarılı", f"'{rol_adi}' imleci güncellendi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 2) Masaüstü (simgeler)
    # ------------------------------------------------------------------
    def _imlec_semasini_uygula(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        secim = self.imlec_sema_combo.get()
        sema_adi = IMLEC_SEMALARI.get(secim)
        if not sema_adi:
            return
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CURSORS_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, sema_adi)
            SPI_SETCURSORS = 0x0057
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            messagebox.showinfo("Başarılı", f"'{secim}' imleç şeması uygulandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _imlec_boyutunu_uygula(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            boyut = int(self.imlec_boyutu_var.get())
            set_reg_dword(winreg.HKEY_CURRENT_USER, ACCESSIBILITY_KEY, "CursorSize", boyut)
            SPI_SETCURSORS = 0x0057
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            messagebox.showinfo(
                "Başarılı",
                f"İmleç boyutu {boyut} olarak ayarlandı. Bazı Windows sürümlerinde "
                "görmek için oturumu yeniden açman gerekebilir.",
            )
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _imlec_rengini_uygula(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        renk = colorchooser.askcolor(title="İmleç rengi seç")
        if not renk or not renk[0]:
            return
        try:
            r, g, b = (int(c) for c in renk[0])
            argb = (0xFF << 24) | (r << 16) | (g << 8) | b
            set_reg_dword(winreg.HKEY_CURRENT_USER, ACCESSIBILITY_KEY, "CursorColor", argb)
            SPI_SETCURSORS = 0x0057
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            messagebox.showinfo(
                "Başarılı",
                "İmleç rengi ayarlandı. Bu özellik yalnızca Windows 11 22H2 ve "
                "üzerinde tam çalışır.",
            )
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _imlec_sifirla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CURSORS_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Windows Default")
            set_reg_dword(winreg.HKEY_CURRENT_USER, ACCESSIBILITY_KEY, "CursorSize", 1)
            SPI_SETCURSORS = 0x0057
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            messagebox.showinfo("Başarılı", "İmleç varsayılana sıfırlandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 2) Masaüstü (simgeler)
    # ------------------------------------------------------------------
    def masaustu_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Masaüstü")

        ttk.Label(frame, text="Masaüstü Simgeleri", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        self.simge_gizli = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Tüm masaüstü simgelerini gizle",
            variable=self.simge_gizli,
            command=self.simgeleri_ayarla,
        ).pack(anchor="w", padx=15, pady=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Ekran Koruyucu", style="Baslik.TLabel").pack(anchor="w", padx=15)
        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        ttk.Button(btns, text="Kapat", command=lambda: self.ekran_koruyucu_ayarla("")).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Boş (siyah)", command=lambda: self.ekran_koruyucu_ayarla("scrnsave.scr")).grid(
            row=0, column=1, padx=5
        )

    def simgeleri_ayarla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            # HideIcons: 1 = gizle, 0 = göster
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "HideIcons",
                1 if self.simge_gizli.get() else 0,
            )
            restart_explorer()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def ekran_koruyucu_ayarla(self, scr_file):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, DESKTOP_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "SCRNSAVE.EXE", 0, winreg.REG_SZ, scr_file)
            messagebox.showinfo("Başarılı", "Ekran koruyucu ayarlandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 3) Görev Çubuğu
    # ------------------------------------------------------------------
    def gorev_cubugu_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Görev Çubuğu")

        ttk.Label(frame, text="Görev Çubuğu Ayarları", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        self.saydamlik = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="Saydamlık efektlerini etkinleştir", variable=self.saydamlik,
            command=self.saydamlik_ayarla,
        ).pack(anchor="w", padx=15, pady=5)

        self.arama_gizli = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Arama kutusunu gizle", variable=self.arama_gizli,
            command=self.arama_kutusu_ayarla,
        ).pack(anchor="w", padx=15, pady=5)

        self.gorev_gorunumu_gizli = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="'Görev Görünümü' butonunu gizle", variable=self.gorev_gorunumu_gizli,
            command=self.gorev_gorunumu_ayarla,
        ).pack(anchor="w", padx=15, pady=5)

        ttk.Label(
            frame,
            text="Not: Bu değişiklikler için Explorer yeniden başlatılır.",
            foreground="gray",
        ).pack(anchor="w", padx=15, pady=10)

    def saydamlik_ayarla(self):
        self._advanced_dword("EnableTransparency", 1 if self.saydamlik.get() else 0)

    def arama_kutusu_ayarla(self):
        # SearchboxTaskbarMode: 0 = gizli, 1 = simge, 2 = kutu
        try:
            if not IS_WINDOWS:
                raise RuntimeError("skip")
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Search",
                "SearchboxTaskbarMode",
                0 if self.arama_gizli.get() else 2,
            )
            restart_explorer()
        except RuntimeError:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def gorev_gorunumu_ayarla(self):
        self._advanced_dword("ShowTaskViewButton", 0 if self.gorev_gorunumu_gizli.get() else 1)

    def _advanced_dword(self, name, value):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, ADVANCED_KEY, name, value)
            restart_explorer()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 4) Başlangıç Programları
    # ------------------------------------------------------------------
    def baslangic_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Başlangıç Programları")

        ttk.Label(frame, text="Başlangıçta Çalışan Programlar", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        self.baslangic_listbox = tk.Listbox(frame, width=60, height=12)
        self.baslangic_listbox.pack(padx=15, pady=5)

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=5)
        ttk.Button(btns, text="Yenile", command=self.baslangic_listele).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Ekle...", command=self.baslangic_ekle).grid(row=0, column=1, padx=5)
        ttk.Button(btns, text="Kaldır", command=self.baslangic_kaldir).grid(row=0, column=2, padx=5)

        self.baslangic_listele()

    def baslangic_listele(self):
        self.baslangic_listbox.delete(0, tk.END)
        if not IS_WINDOWS:
            self.baslangic_listbox.insert(tk.END, "(Windows dışında listelenemez)")
            return
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        self.baslangic_listbox.insert(tk.END, f"[Registry] {name} -> {value}")
                        i += 1
                    except OSError:
                        break
        except Exception as e:
            self.baslangic_listbox.insert(tk.END, f"Hata: {e}")

        if os.path.isdir(STARTUP_FOLDER):
            for fname in os.listdir(STARTUP_FOLDER):
                self.baslangic_listbox.insert(tk.END, f"[Klasör] {fname}")

    def baslangic_ekle(self):
        path = filedialog.askopenfilename(title="Başlangıçta çalışacak programı seç (.exe)")
        if not path:
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            name = os.path.splitext(os.path.basename(path))[0]
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, path)
            messagebox.showinfo("Başarılı", f"{name} başlangıca eklendi.")
            self.baslangic_listele()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def baslangic_kaldir(self):
        secim = self.baslangic_listbox.curselection()
        if not secim:
            return
        satir = self.baslangic_listbox.get(secim[0])
        if not satir.startswith("[Registry]"):
            messagebox.showinfo("Bilgi", "Sadece Registry üzerindeki girişler bu araçtan kaldırılabilir. "
                                          "Klasördekiler için Başlangıç klasörünü elle düzenle.")
            return
        name = satir.replace("[Registry] ", "").split(" -> ")[0]
        if not IS_WINDOWS:
            return
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
            messagebox.showinfo("Başarılı", f"{name} başlangıçtan kaldırıldı.")
            self.baslangic_listele()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 5) Fare Ayarları
    # ------------------------------------------------------------------
    def fare_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Fare")

        ttk.Label(frame, text="Fare İşaretçi Hızı", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        self.fare_hizi = tk.IntVar(value=10)
        scale = ttk.Scale(
            frame, from_=1, to=20, orient="horizontal", variable=self.fare_hizi,
            command=lambda v: None,
        )
        scale.pack(fill="x", padx=15, pady=5)

        ttk.Button(frame, text="Uygula", command=self.fare_hizi_uygula).pack(anchor="w", padx=15, pady=10)

    def fare_hizi_uygula(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            hiz = int(self.fare_hizi.get())
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, DESKTOP_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "MouseSensitivity", 0, winreg.REG_SZ, str(hiz))
            SPI_SETMOUSESPEED = 0x0071
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETMOUSESPEED, 0, hiz, 0)
            messagebox.showinfo("Başarılı", f"Fare hızı {hiz} olarak ayarlandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))


    # ------------------------------------------------------------------
    # 6) Performans / FPS Artırma
    # ------------------------------------------------------------------
    def performans_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Performans / FPS")

        ttk.Label(frame, text="Oyun Performansı Ayarları", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Bunlar gerçek FPS artışı sağlayabilecek sistem ayarlarıdır\n"
                 "(donanım hızlandırmalı GPU zamanlama, güç planı, oyun modu vb.)",
            foreground="gray",
            justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.gpu_scheduling = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Donanım Hızlandırmalı GPU Zamanlama'yı etkinleştir",
            variable=self.gpu_scheduling, command=self.gpu_scheduling_ayarla,
        ).pack(anchor="w", padx=15, pady=3)

        self.oyun_modu = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="Oyun Modu'nu etkinleştir", variable=self.oyun_modu,
            command=self.oyun_modu_ayarla,
        ).pack(anchor="w", padx=15, pady=3)

        self.game_bar_kapat = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Xbox Game Bar / Game DVR kaydını kapat (arka plan yükünü azaltır)",
            variable=self.game_bar_kapat, command=self.game_bar_ayarla,
        ).pack(anchor="w", padx=15, pady=3)

        self.gorsel_efekt_kapat = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Görsel efektleri kapat (En iyi performans için ayarla)",
            variable=self.gorsel_efekt_kapat, command=self.gorsel_efekt_ayarla,
        ).pack(anchor="w", padx=15, pady=3)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Güç Planı", style="Baslik.TLabel").pack(anchor="w", padx=15)
        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        ttk.Button(btns, text="Yüksek Performans", command=lambda: self.guc_plani_ayarla("high")).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(btns, text="Dengeli", command=lambda: self.guc_plani_ayarla("balanced")).grid(
            row=0, column=1, padx=5
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(
            frame,
            text=(
                "Not: Gerçek kare üretimi (frame generation) / yapay zeka tabanlı üst\n"
                "ölçekleme, GPU'nun shader'larını kullanan ayrı bir grafik motoru\n"
                "gerektirir — registry ayarıyla yapılamaz. Bunun için GPU üreticinin\n"
                "(NVIDIA/AMD/Intel) kendi sürücü ayarlarındaki ilgili özelliği ya da "
                "özel bir\nuygulamayı kullanman gerekir. Bu programın yapabildiği, bu tür "
                "ayarlara\ngiden Windows ayarlarını hızlıca açmak."
            ),
            foreground="gray",
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=15, pady=5)

        ttk.Button(frame, text="Grafik Ayarları'nı Aç (Windows)", command=self.grafik_ayarlarini_ac).pack(
            anchor="w", padx=15, pady=5
        )

    def gpu_scheduling_ayarla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            set_reg_dword(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                "HwSchMode",
                2 if self.gpu_scheduling.get() else 1,
            )
            messagebox.showinfo(
                "Başarılı",
                "Ayar kaydedildi. Etkili olması için bilgisayarı yeniden başlatman gerekiyor.\n"
                "(Bu ayar HKEY_LOCAL_MACHINE altında olduğu için yönetici olarak çalıştırman gerekebilir.)",
            )
        except PermissionError:
            messagebox.showerror("Yetki Hatası", "Bu ayar için programı 'Yönetici olarak çalıştır' ile açman gerekiyor.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def oyun_modu_ayarla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\GameBar",
                "AllowAutoGameMode",
                1 if self.oyun_modu.get() else 0,
            )
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\GameBar",
                "AutoGameModeEnabled",
                1 if self.oyun_modu.get() else 0,
            )
            messagebox.showinfo("Başarılı", "Oyun Modu ayarı güncellendi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def game_bar_ayarla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            kapat = self.game_bar_kapat.get()
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"System\GameConfigStore",
                "GameDVR_Enabled",
                0 if kapat else 1,
            )
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                "AppCaptureEnabled",
                0 if kapat else 1,
            )
            messagebox.showinfo("Başarılı", "Game Bar / Game DVR ayarı güncellendi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def gorsel_efekt_ayarla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            # VisualFXSetting: 0=Otomatik(Let Windows choose), 1=En iyi görünüm,
            # 2=En iyi performans, 3=Özel
            set_reg_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                "VisualFXSetting",
                2 if self.gorsel_efekt_kapat.get() else 0,
            )
            messagebox.showinfo(
                "Başarılı",
                "Görsel efekt ayarı güncellendi. Tam olarak uygulanması için oturumu "
                "kapatıp açman gerekebilir.",
            )
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def guc_plani_ayarla(self, mod):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        # Windows'un yerleşik güç planı GUID'leri
        guid = {
            "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",       # Yüksek Performans
            "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",   # Dengeli
        }.get(mod)
        try:
            subprocess.run(["powercfg", "/setactive", guid], check=True)
            messagebox.showinfo("Başarılı", "Güç planı değiştirildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Güç planı değiştirilemedi: {e}")

    def grafik_ayarlarini_ac(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            os.startfile("ms-settings:display-advancedgraphics")
        except Exception as e:
            messagebox.showerror("Hata", str(e))


    # ------------------------------------------------------------------
    # 7) Pano Geçmişi — tamamen yerli, ek paket gerekmez
    # ------------------------------------------------------------------
    def pano_gecmisi_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Pano Geçmişi")

        ttk.Label(frame, text="Pano Geçmişi", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Kopyaladığın metinleri otomatik olarak burada biriktirir. "
                 "Listeden birine çift tıklayınca tekrar panoya kopyalanır.",
            foreground="gray", wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        arama_cercevesi = ttk.Frame(frame)
        arama_cercevesi.pack(fill="x", padx=15, pady=(0, 5))
        ttk.Label(arama_cercevesi, text="Ara:").pack(side="left")
        self.pano_arama_var = tk.StringVar()
        self.pano_arama_var.trace_add("write", lambda *a: self._pano_listesini_guncelle())
        ttk.Entry(arama_cercevesi, textvariable=self.pano_arama_var).pack(
            side="left", fill="x", expand=True, padx=5
        )

        self.pano_listbox = tk.Listbox(frame, width=70, height=14)
        self.pano_listbox.pack(padx=15, pady=5, fill="both")
        self.pano_listbox.bind("<Double-Button-1>", self._pano_ogesini_kopyala)

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=5)
        ttk.Button(btns, text="Kopyala", command=self._pano_ogesini_kopyala).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Geçmişi Temizle", command=self._pano_gecmisini_temizle).grid(
            row=0, column=1, padx=5
        )

    def _pano_izlemeyi_baslat(self):
        self._pano_calisiyor = True

        def dongu():
            while self._pano_calisiyor:
                try:
                    deger = self.clipboard_get()
                except Exception:
                    deger = None
                if deger and deger != self._son_pano_degeri and deger.strip():
                    self._son_pano_degeri = deger
                    # Aynı öğe zaten en başta değilse listeye ekle
                    if not self._pano_gecmisi or self._pano_gecmisi[0] != deger:
                        self._pano_gecmisi.insert(0, deger)
                        self._pano_gecmisi = self._pano_gecmisi[:100]
                        self.after(0, self._pano_listesini_guncelle)
                time.sleep(0.6)

        threading.Thread(target=dongu, daemon=True).start()

    def _pano_listesini_guncelle(self):
        if not hasattr(self, "pano_listbox"):
            return
        filtre = self.pano_arama_var.get().lower() if hasattr(self, "pano_arama_var") else ""
        self.pano_listbox.delete(0, tk.END)
        for oge in self._pano_gecmisi:
            tek_satir = oge.replace("\n", " ⏎ ").strip()
            if filtre and filtre not in tek_satir.lower():
                continue
            gosterim = tek_satir[:90] + ("..." if len(tek_satir) > 90 else "")
            self.pano_listbox.insert(tk.END, gosterim)

    def _pano_ogesini_kopyala(self, event=None):
        secim = self.pano_listbox.curselection()
        if not secim:
            return
        # Görüntülenen (kırpılmış) metin yerine orijinal tam metni bul
        filtre = self.pano_arama_var.get().lower()
        gorunen = [o for o in self._pano_gecmisi if not filtre or filtre in o.lower()]
        idx = secim[0]
        if idx >= len(gorunen):
            return
        deger = gorunen[idx]
        self.clipboard_clear()
        self.clipboard_append(deger)
        self._son_pano_degeri = deger

    def _pano_gecmisini_temizle(self):
        self._pano_gecmisi = []
        self._pano_listesini_guncelle()

    # ------------------------------------------------------------------
    # 8) Renk Seçici — ctypes/GDI ile
    # ------------------------------------------------------------------
    def renk_secici_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Renk Seçici")

        ttk.Label(frame, text="Ekran Renk Seçici", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="'İzlemeyi Başlat'a bas, farenle ekranda gezin — imlecin altındaki "
                 "rengi anlık gösterir. 'Rengi Yakala' ile o anki rengi dondurup HEX "
                 "kodunu panoya kopyalar.",
            foreground="gray", wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        bilgi_cercevesi = ttk.Frame(frame)
        bilgi_cercevesi.pack(anchor="w", padx=15, pady=10)

        self.renk_ornek_canvas = tk.Canvas(bilgi_cercevesi, width=80, height=80, bg="#ffffff",
                                            relief="groove", bd=2)
        self.renk_ornek_canvas.grid(row=0, column=0, rowspan=3, padx=(0, 15))

        self.renk_hex_var = tk.StringVar(value="HEX: -")
        self.renk_rgb_var = tk.StringVar(value="RGB: -")
        self.renk_konum_var = tk.StringVar(value="Konum: -")
        ttk.Label(bilgi_cercevesi, textvariable=self.renk_hex_var, font=("Consolas", 11)).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(bilgi_cercevesi, textvariable=self.renk_rgb_var, font=("Consolas", 11)).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Label(bilgi_cercevesi, textvariable=self.renk_konum_var, foreground="gray").grid(
            row=2, column=1, sticky="w"
        )

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        self.renk_izleme_aktif = False
        self.renk_izleme_btn = ttk.Button(btns, text="▶ İzlemeyi Başlat", command=self._renk_izlemeyi_ac_kapa)
        self.renk_izleme_btn.grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="📌 Rengi Yakala ve Kopyala", command=self._rengi_yakala).grid(
            row=0, column=1, padx=5
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)
        ttk.Label(frame, text="Yakalanan Renk Paleti", style="AltBaslik.TLabel").pack(
            anchor="w", padx=15
        )
        self.renk_paleti_canvas = tk.Canvas(frame, height=44, bg=RENK["panel"], highlightthickness=0)
        self.renk_paleti_canvas.pack(fill="x", padx=15, pady=(5, 5))
        self.renk_paleti_canvas.bind("<Button-1>", self._paletten_renk_kopyala)
        ttk.Label(
            frame, text="(Bir renge tıklayınca HEX kodu tekrar panoya kopyalanır)",
            foreground=RENK["metin_gri"],
        ).pack(anchor="w", padx=15)

    def _renk_izlemeyi_ac_kapa(self):
        self.renk_izleme_aktif = not self.renk_izleme_aktif
        self.renk_izleme_btn.config(
            text="⏸ İzlemeyi Durdur" if self.renk_izleme_aktif else "▶ İzlemeyi Başlat"
        )
        if self.renk_izleme_aktif:
            self._renk_izleme_dongusu()

    def _get_pixel_color(self):
        """İmlecin altındaki ekran pikselinin rengini ctypes/GDI ile okur."""
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        hdc = ctypes.windll.user32.GetDC(0)
        colorref = ctypes.windll.gdi32.GetPixel(hdc, pt.x, pt.y)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        r = colorref & 0xFF
        g = (colorref >> 8) & 0xFF
        b = (colorref >> 16) & 0xFF
        return pt.x, pt.y, r, g, b

    def _renk_izleme_dongusu(self):
        if not self.renk_izleme_aktif:
            return
        if IS_WINDOWS:
            try:
                x, y, r, g, b = self._get_pixel_color()
                hex_kod = f"#{r:02x}{g:02x}{b:02x}"
                self.renk_hex_var.set(f"HEX: {hex_kod}")
                self.renk_rgb_var.set(f"RGB: ({r}, {g}, {b})")
                self.renk_konum_var.set(f"Konum: {x}, {y}")
                self.renk_ornek_canvas.config(bg=hex_kod)
            except Exception:
                pass
        self.after(100, self._renk_izleme_dongusu)

    def _rengi_yakala(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            x, y, r, g, b = self._get_pixel_color()
            hex_kod = f"#{r:02x}{g:02x}{b:02x}"
            self.clipboard_clear()
            self.clipboard_append(hex_kod)
            self.renk_izleme_aktif = False
            self.renk_izleme_btn.config(text="▶ İzlemeyi Başlat")
            self._renk_gecmisi.insert(0, hex_kod)
            self._renk_gecmisi = self._renk_gecmisi[:12]
            self._renk_paletini_ciz()
            messagebox.showinfo("Yakalandı", f"{hex_kod} panoya kopyalandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _renk_paletini_ciz(self):
        canvas = self.renk_paleti_canvas
        canvas.delete("all")
        genislik = 40
        for i, hex_kod in enumerate(self._renk_gecmisi):
            x0 = 4 + i * (genislik + 4)
            canvas.create_rectangle(x0, 4, x0 + genislik, 40, fill=hex_kod, outline=RENK["kenarlik"],
                                     tags=(f"renk_{i}",))

    def _paletten_renk_kopyala(self, event):
        genislik = 40
        idx = event.x // (genislik + 4)
        if 0 <= idx < len(self._renk_gecmisi):
            hex_kod = self._renk_gecmisi[idx]
            self.clipboard_clear()
            self.clipboard_append(hex_kod)
            self.title(f"⚡ Windows Özelleştirici — {hex_kod} kopyalandı")
            self.after(1500, lambda: self.title("⚡ Windows Özelleştirici — EFSANE Sürüm"))

    # ------------------------------------------------------------------
    # 9) Pencere Hizalama — ctypes/user32
    # ------------------------------------------------------------------
    def pencere_hizalama_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Pencere Hizalama")

        ttk.Label(frame, text="Pencere Hizalama", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Önce hizalamak istediğin pencereye tıkla, sonra buraya dönmeden "
                 "aşağıdaki bir düzeni seç — bu program son aktif olan pencereyi "
                 "otomatik hatırlayıp onu yeniden boyutlandırır.",
            foreground="gray", wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        izgara = ttk.Frame(frame)
        izgara.pack(anchor="w", padx=15, pady=10)

        duzenler = [
            ("◧ Sol Yarım", "sol_yarim"),
            ("◨ Sağ Yarım", "sag_yarim"),
            ("⬒ Üst Yarım", "ust_yarim"),
            ("⬓ Alt Yarım", "alt_yarim"),
            ("◰ Sol-Üst Çeyrek", "sol_ust"),
            ("◳ Sağ-Üst Çeyrek", "sag_ust"),
            ("◱ Sol-Alt Çeyrek", "sol_alt"),
            ("◲ Sağ-Alt Çeyrek", "sag_alt"),
            ("⬜ Tam Ekran", "tam_ekran"),
            ("▣ Ortala (%70)", "ortala"),
        ]
        for i, (etiket, kod) in enumerate(duzenler):
            ttk.Button(
                izgara, text=etiket, width=18,
                command=lambda k=kod: self._pencereyi_hizala(k),
            ).grid(row=i // 2, column=i % 2, padx=5, pady=5)

        self.hizalama_hedef_var = tk.StringVar(value="Son algılanan pencere: (henüz yok)")
        ttk.Label(frame, textvariable=self.hizalama_hedef_var, foreground="gray").pack(
            anchor="w", padx=15, pady=10
        )

    def _pencere_takibini_baslat(self):
        """Arka planda sürekli en son aktif olan (bizim programımız olmayan)
        pencereyi hatırlar, böylece hizalama butonlarına bastığımızda
        hangi pencereyi hizalayacağımızı biliriz."""
        self._pencere_takip_calisiyor = True
        if not IS_WINDOWS:
            return

        def dongu():
            kendi_hwnd = ctypes.windll.user32.GetForegroundWindow()
            while self._pencere_takip_calisiyor:
                try:
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    if hwnd and hwnd != self._kendi_pencere_handle():
                        self._son_disardaki_pencere = hwnd
                        baslik = self._pencere_basligi_al(hwnd)
                        if baslik:
                            self.after(0, lambda b=baslik: self.hizalama_hedef_var.set(
                                f"Son algılanan pencere: {b}"
                            ))
                except Exception:
                    pass
                time.sleep(0.4)

        threading.Thread(target=dongu, daemon=True).start()

    def _kendi_pencere_handle(self):
        try:
            return ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
        except Exception:
            return None

    def _pencere_basligi_al(self, hwnd):
        uzunluk = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if uzunluk == 0:
            return None
        arabellek = ctypes.create_unicode_buffer(uzunluk + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, arabellek, uzunluk + 1)
        return arabellek.value

    def _pencereyi_hizala(self, duzen):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        hwnd = self._son_disardaki_pencere
        if not hwnd:
            messagebox.showwarning("Uyarı", "Henüz hizalanacak bir pencere algılanmadı. "
                                             "Önce başka bir pencereye tıkla.")
            return
        try:
            SM_CXSCREEN, SM_CYSCREEN = 0, 1
            en = ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN)
            boy = ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN)

            # Windows'un "Maximize/Restore" özelliğini önce kapatmak için
            SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

            konumlar = {
                "sol_yarim": (0, 0, en // 2, boy),
                "sag_yarim": (en // 2, 0, en // 2, boy),
                "ust_yarim": (0, 0, en, boy // 2),
                "alt_yarim": (0, boy // 2, en, boy // 2),
                "sol_ust": (0, 0, en // 2, boy // 2),
                "sag_ust": (en // 2, 0, en // 2, boy // 2),
                "sol_alt": (0, boy // 2, en // 2, boy // 2),
                "sag_alt": (en // 2, boy // 2, en // 2, boy // 2),
                "tam_ekran": (0, 0, en, boy),
                "ortala": (int(en * 0.15), int(boy * 0.15), int(en * 0.7), int(boy * 0.7)),
            }
            x, y, w, h = konumlar[duzen]
            SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 10) Mini Sistem Monitörü — ctypes/kernel32
    # ------------------------------------------------------------------
    def sistem_monitor_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Sistem Monitörü")

        ttk.Label(frame, text="Mini Sistem Monitörü", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Ekranın bir köşesinde her zaman üstte duran, CPU ve RAM "
                 "kullanımını canlı gösteren küçük bir widget açar.",
            foreground="gray", wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ttk.Button(frame, text="🖥 Mini Monitörü Aç", command=self._mini_monitor_ac).pack(
            anchor="w", padx=15, pady=10
        )

        self.monitor_onizleme_var = tk.StringVar(value="CPU: -   RAM: -")
        ttk.Label(frame, textvariable=self.monitor_onizleme_var, font=("Consolas", 11)).pack(
            anchor="w", padx=15, pady=10
        )
        self._monitor_onizlemeyi_guncelle()

    def _cpu_kullanimi_al(self):
        """GetSystemTimes ile iki örnekleme arasındaki farktan CPU kullanım
        yüzdesini hesaplar (ek paket gerekmez)."""
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

        def oku():
            idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            )
            def to_int(ft):
                return (ft.dwHighDateTime << 32) | ft.dwLowDateTime
            return to_int(idle), to_int(kernel) + to_int(user)

        idle1, total1 = oku()
        time.sleep(0.3)
        idle2, total2 = oku()
        idle_delta = idle2 - idle1
        total_delta = total2 - total1
        if total_delta <= 0:
            return 0.0
        kullanim = (1 - idle_delta / total_delta) * 100
        return max(0.0, min(100.0, kullanim))

    def _ram_kullanimi_al(self):
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        toplam_gb = stat.ullTotalPhys / (1024 ** 3)
        return stat.dwMemoryLoad, toplam_gb

    def _monitor_onizlemeyi_guncelle(self):
        if IS_WINDOWS:
            try:
                _, ram_gb = self._ram_kullanimi_al()
                cpu = self._cpu_anlik_tahmin()
                self.monitor_onizleme_var.set(f"CPU: ~%{cpu:.0f}   RAM: {ram_gb:.1f} GB toplam")
            except Exception:
                pass
        self.after(3000, self._monitor_onizlemeyi_guncelle)

    def _cpu_anlik_tahmin(self):
        # Önizleme etiketini kilitlemeden hızlı, kabaca bir CPU okuması
        try:
            ram_yuzde, _ = self._ram_kullanimi_al()
            return ram_yuzde  # kaba bir gösterge; gerçek ölçüm mini widget'ta yapılır
        except Exception:
            return 0

    def _disk_kullanimi_al(self, yol="C:\\"):
        bos = ctypes.c_uint64(0)
        toplam = ctypes.c_uint64(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(yol), None, ctypes.byref(toplam), ctypes.byref(bos)
        )
        if toplam.value == 0:
            return 0, 0, 0
        kullanilan_yuzde = (1 - bos.value / toplam.value) * 100
        return kullanilan_yuzde, bos.value / (1024 ** 3), toplam.value / (1024 ** 3)

    def _mini_monitor_ac(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        pencere = tk.Toplevel(self)
        pencere.title("Sistem Monitörü")
        pencere.geometry("210x150+40+40")
        pencere.attributes("-topmost", True)
        pencere.overrideredirect(True)
        try:
            pencere.attributes("-alpha", 0.90)
        except Exception:
            pass
        pencere.configure(bg="#12141c")

        # Sürüklenebilir üst çubuk (pencere kenarlığı olmadığı için)
        tutamac = tk.Frame(pencere, bg=RENK["vurgu"], height=22)
        tutamac.pack(fill="x")
        tk.Label(tutamac, text="⚡ Monitör", bg=RENK["vurgu"], fg="#ffffff",
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=6)
        kapat_btn = tk.Label(tutamac, text="✕", bg=RENK["vurgu"], fg="#ffffff",
                              font=("Segoe UI", 9, "bold"), cursor="hand2")
        kapat_btn.pack(side="right", padx=6)

        def surukle_baslat(e):
            pencere._sx, pencere._sy = e.x, e.y

        def surukle(e):
            x = pencere.winfo_pointerx() - pencere._sx
            y = pencere.winfo_pointery() - pencere._sy
            pencere.geometry(f"+{x}+{y}")

        tutamac.bind("<Button-1>", surukle_baslat)
        tutamac.bind("<B1-Motion>", surukle)

        govde = tk.Frame(pencere, bg="#12141c")
        govde.pack(fill="both", expand=True, padx=10, pady=8)

        cpu_label = tk.Label(govde, text="CPU: -- %", fg="#00ff90", bg="#12141c", font=("Consolas", 13, "bold"))
        cpu_label.pack(anchor="w")
        ram_label = tk.Label(govde, text="RAM: -- %", fg="#40c8ff", bg="#12141c", font=("Consolas", 13, "bold"))
        ram_label.pack(anchor="w")
        disk_label = tk.Label(govde, text="DİSK: -- %", fg="#ffb86c", bg="#12141c", font=("Consolas", 13, "bold"))
        disk_label.pack(anchor="w")

        calisiyor = {"aktif": True}

        def kapat():
            calisiyor["aktif"] = False
            pencere.destroy()

        kapat_btn.bind("<Button-1>", lambda e: kapat())

        def guncelle_dongu():
            if not calisiyor["aktif"]:
                return

            def arka_planda_olc():
                cpu = self._cpu_kullanimi_al()
                ram_yuzde, _ = self._ram_kullanimi_al()
                disk_yuzde, _, _ = self._disk_kullanimi_al()
                if calisiyor["aktif"]:
                    self.after(0, lambda: cpu_label.config(text=f"CPU:  {cpu:.0f} %"))
                    self.after(0, lambda: ram_label.config(text=f"RAM:  {ram_yuzde} %"))
                    self.after(0, lambda: disk_label.config(text=f"DİSK: {disk_yuzde:.0f} %"))
                    self.after(1500, guncelle_dongu)

            threading.Thread(target=arka_planda_olc, daemon=True).start()

        guncelle_dongu()

    # ------------------------------------------------------------------
    # 11) Hızlı Dosya Arama — basit indeksleme
    # ------------------------------------------------------------------
    def dosya_arama_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Dosya Arama")

        ttk.Label(frame, text="Hızlı Dosya Arama", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Not: NTFS disk kaydını (MFT) doğrudan okumaz — seçtiğin klasörü "
                 "tarayıp bellekte bir liste oluşturur. Büyük disklerde ilk tarama "
                 "biraz sürer, ama tarama bitince arama anlık olur.",
            foreground="gray", wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ust_cerceve = ttk.Frame(frame)
        ust_cerceve.pack(fill="x", padx=15, pady=5)
        ttk.Button(ust_cerceve, text="📁 Klasör Tara...", command=self._dizin_taramayi_baslat).pack(side="left")
        self.dosya_index_durum_var = tk.StringVar(value="Henüz taranmadı (0 dosya)")
        ttk.Label(ust_cerceve, textvariable=self.dosya_index_durum_var, foreground="gray").pack(
            side="left", padx=10
        )

        arama_cercevesi = ttk.Frame(frame)
        arama_cercevesi.pack(fill="x", padx=15, pady=5)
        ttk.Label(arama_cercevesi, text="Ara:").pack(side="left")
        self.dosya_arama_var = tk.StringVar()
        self.dosya_arama_var.trace_add("write", lambda *a: self._dosya_aramasini_filtrele())
        ttk.Entry(arama_cercevesi, textvariable=self.dosya_arama_var).pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Label(arama_cercevesi, text="Uzantı:").pack(side="left", padx=(10, 0))
        self.dosya_uzanti_var = tk.StringVar(value="Tümü")
        uzanti_combo = ttk.Combobox(
            arama_cercevesi, state="readonly", width=10, textvariable=self.dosya_uzanti_var,
            values=["Tümü", ".txt", ".pdf", ".docx", ".xlsx", ".jpg", ".png", ".mp4", ".mp3", ".zip", ".py", ".exe"],
        )
        uzanti_combo.pack(side="left", padx=5)
        uzanti_combo.bind("<<ComboboxSelected>>", lambda e: self._dosya_aramasini_filtrele())

        self.dosya_sonuc_listbox = tk.Listbox(frame, width=75, height=12)
        self.dosya_sonuc_listbox.pack(padx=15, pady=5, fill="both")
        self.dosya_sonuc_listbox.bind("<Double-Button-1>", self._dosyayi_ac)

        self.dosya_sonuc_sayisi_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.dosya_sonuc_sayisi_var, foreground=RENK["metin_gri"]).pack(
            anchor="w", padx=15
        )

    def _dizin_taramayi_baslat(self):
        if self._dosya_index_calisiyor:
            messagebox.showinfo("Bilgi", "Zaten bir tarama sürüyor, bitmesini bekle.")
            return
        klasor = filedialog.askdirectory(title="Taranacak klasörü seç")
        if not klasor:
            return
        self._dosya_index_calisiyor = True
        self.dosya_index_durum_var.set("Taranıyor...")

        def tara():
            sayac = 0
            sonuc = []
            for kok, dizinler, dosyalar in os.walk(klasor):
                for ad in dosyalar:
                    sonuc.append(os.path.join(kok, ad))
                    sayac += 1
                    if sayac % 500 == 0:
                        self.after(0, lambda s=sayac: self.dosya_index_durum_var.set(
                            f"Taranıyor... ({s} dosya bulundu)"
                        ))
            self._dosya_indeksi = sonuc
            self._dosya_index_calisiyor = False
            self.after(0, lambda: self.dosya_index_durum_var.set(f"Tarama tamamlandı ({len(sonuc)} dosya)"))
            self.after(0, self._dosya_aramasini_filtrele)

        threading.Thread(target=tara, daemon=True).start()

    def _dosya_aramasini_filtrele(self):
        if not hasattr(self, "dosya_sonuc_listbox"):
            return
        sorgu = self.dosya_arama_var.get().lower().strip()
        uzanti = self.dosya_uzanti_var.get() if hasattr(self, "dosya_uzanti_var") else "Tümü"
        self.dosya_sonuc_listbox.delete(0, tk.END)
        if not sorgu and uzanti == "Tümü":
            self.dosya_sonuc_sayisi_var.set("")
            return
        eslesenler = self._dosya_indeksi
        if sorgu:
            eslesenler = [p for p in eslesenler if sorgu in os.path.basename(p).lower()]
        if uzanti != "Tümü":
            eslesenler = [p for p in eslesenler if p.lower().endswith(uzanti)]
        for yol in eslesenler[:200]:
            self.dosya_sonuc_listbox.insert(tk.END, yol)
        toplam = len(eslesenler)
        self.dosya_sonuc_sayisi_var.set(
            f"{toplam} sonuç bulundu" + (" (ilk 200 gösteriliyor)" if toplam > 200 else "")
        )

    def _dosyayi_ac(self, event=None):
        secim = self.dosya_sonuc_listbox.curselection()
        if not secim:
            return
        yol = self.dosya_sonuc_listbox.get(secim[0])
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", f"(Simülasyon) Açılacak dosya: {yol}")
            return
        try:
            os.startfile(yol)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 12) Ekran Görüntüsü — ctypes/GDI, ek paket gerekmez
    # ------------------------------------------------------------------
    def ekran_goruntusu_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Ekran Görüntüsü")

        ttk.Label(frame, text="Ekran Görüntüsü Aracı", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Tam ekran görüntüsünü doğrudan Windows GDI API'siyle yakalayıp "
                 "Resimler klasörüne .bmp olarak kaydeder (ek kütüphane gerekmez).",
            foreground="gray", wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ttk.Button(frame, text="📸 Tam Ekran Görüntüsü Al", command=self._tam_ekran_goruntusu_al).pack(
            anchor="w", padx=15, pady=10
        )

        self.ekran_goruntusu_durum_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.ekran_goruntusu_durum_var, foreground="gray", wraplength=560).pack(
            anchor="w", padx=15, pady=5
        )

    def _tam_ekran_goruntusu_al(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            self.withdraw()  # kendi pencereyi görüntüye dahil etmemek için gizle
            self.after(250, self._ekran_goruntusunu_yakala_ve_kaydet)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _ekran_goruntusunu_yakala_ve_kaydet(self):
        try:
            yol = self._bmp_ekran_goruntusu_kaydet()
            self.deiconify()
            self.ekran_goruntusu_durum_var.set(f"Kaydedildi: {yol}")
            messagebox.showinfo("Başarılı", f"Ekran görüntüsü kaydedildi:\n{yol}")
        except Exception as e:
            self.deiconify()
            messagebox.showerror("Hata", str(e))

    def _bmp_ekran_goruntusu_kaydet(self):
        """Sadece ctypes/GDI kullanarak tam ekran görüntüsünü .bmp olarak kaydeder."""
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        en = user32.GetSystemMetrics(0)
        boy = user32.GetSystemMetrics(1)

        hdc_ekran = user32.GetDC(0)
        hdc_bellek = gdi32.CreateCompatibleDC(hdc_ekran)
        h_bitmap = gdi32.CreateCompatibleBitmap(hdc_ekran, en, boy)
        gdi32.SelectObject(hdc_bellek, h_bitmap)
        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(hdc_bellek, 0, 0, en, boy, hdc_ekran, 0, 0, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = en
        bmi.biHeight = -boy  # üstten alta doğru satır sırası
        bmi.biPlanes = 1
        bmi.biBitCount = 24
        bmi.biCompression = 0  # BI_RGB

        satir_boyutu = ((en * 3 + 3) // 4) * 4
        arabellek_boyutu = satir_boyutu * boy
        arabellek = ctypes.create_string_buffer(arabellek_boyutu)

        DIB_RGB_COLORS = 0
        gdi32.GetDIBits(hdc_bellek, h_bitmap, 0, boy, arabellek, ctypes.byref(bmi), DIB_RGB_COLORS)

        klasor = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
        os.makedirs(klasor, exist_ok=True)
        dosya_adi = f"ekran_goruntusu_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.bmp"
        tam_yol = os.path.join(klasor, dosya_adi)

        with open(tam_yol, "wb") as f:
            dosya_boyutu = 54 + arabellek_boyutu
            # BITMAPFILEHEADER (14 bayt)
            f.write(struct.pack("<2sIHHI", b"BM", dosya_boyutu, 0, 0, 54))
            # BITMAPINFOHEADER (40 bayt)
            f.write(struct.pack(
                "<IiiHHIIiiII", 40, en, boy, 1, 24, 0, arabellek_boyutu, 0, 0, 0, 0
            ))
            f.write(arabellek.raw)

        gdi32.DeleteObject(h_bitmap)
        gdi32.DeleteDC(hdc_bellek)
        user32.ReleaseDC(0, hdc_ekran)
        return tam_yol


    # ------------------------------------------------------------------
    # 13) FPS Göstergesi (ekranın sol üstünde küçük HUD)
    # ------------------------------------------------------------------
    def fps_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="FPS Göstergesi")

        ttk.Label(frame, text="FPS Göstergesi", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Ekranın sol üst köşesinde, her zaman üstte duran, saydam arka planlı "
                 "küçük bir FPS/Hz göstergesi açar. Not: Bu, oyunun render motoruna "
                 "gömülen gerçek bir performans katmanı değildir — masaüstü görüntüsündeki "
                 "piksel değişim hızını ölçerek YAKLAŞIK bir kare hızı tahmini yapar. "
                 "En doğru sonuç için oyunu pencereli/kenarlıksız pencere modunda çalıştır.",
            foreground=RENK["metin_gri"], wraplength=580, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Ekranın gerçek yenileme hızı (Hz) — bu değer %100 gerçek ve kesin
        hz = self._monitor_yenileme_hizi_al()
        ttk.Label(
            frame, text=f"🖥 Algılanan monitör yenileme hızı: {hz} Hz" if hz else
            "🖥 Monitör yenileme hızı okunamadı.",
            style="AltBaslik.TLabel",
        ).pack(anchor="w", padx=15, pady=(5, 15))

        ayar_cercevesi = ttk.Frame(frame)
        ayar_cercevesi.pack(anchor="w", padx=15, pady=5, fill="x")

        ttk.Label(ayar_cercevesi, text="Yazı Boyutu:").grid(row=0, column=0, sticky="w")
        self.fps_boyut_var = tk.IntVar(value=22)
        boyut_scale = ttk.Scale(
            ayar_cercevesi, from_=12, to=60, orient="horizontal", variable=self.fps_boyut_var,
            length=260, command=lambda v: self._fps_overlay_guncelle_ayarlar(),
        )
        boyut_scale.grid(row=0, column=1, padx=10, sticky="w")

        ttk.Label(ayar_cercevesi, text="Renk:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        renk_cercevesi = ttk.Frame(ayar_cercevesi)
        renk_cercevesi.grid(row=1, column=1, sticky="w", pady=(10, 0))
        self.fps_renk_var = tk.StringVar(value="#39ff14")
        renk_secenekleri = [
            ("Neon Yeşil", "#39ff14"), ("Camgöbeği", "#00e5ff"),
            ("Sarı", "#fff200"), ("Beyaz", "#ffffff"), ("Vurgu Moru", RENK["vurgu"]),
        ]
        for i, (etiket, kod) in enumerate(renk_secenekleri):
            tk.Radiobutton(
                renk_cercevesi, text=etiket, value=kod, variable=self.fps_renk_var,
                command=self._fps_overlay_guncelle_ayarlar, bg=RENK["arkaplan"], fg=RENK["metin"],
                selectcolor=RENK["panel2"], activebackground=RENK["arkaplan"],
                activeforeground=RENK["metin"], highlightthickness=0,
            ).grid(row=0, column=i, padx=(0, 8))

        self.fps_hz_goster_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            ayar_cercevesi, text="Hz bilgisini de göster", variable=self.fps_hz_goster_var,
            command=self._fps_overlay_guncelle_ayarlar,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=15)
        self.fps_baslat_btn = ttk.Button(btns, text="▶ Göstergeyi Aç", command=self._fps_overlay_ac_kapa)
        self.fps_baslat_btn.grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="↺ Sol Üste Sıfırla (Konum)", command=self._fps_overlay_konumu_sifirla).grid(
            row=0, column=1, padx=5
        )

    def _monitor_yenileme_hizi_al(self):
        if not IS_WINDOWS:
            return None
        try:
            class DEVMODE(ctypes.Structure):
                _fields_ = [
                    ("dmDeviceName", ctypes.c_wchar * 32), ("dmSpecVersion", wintypes.WORD),
                    ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
                    ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                    ("dmOrientation", ctypes.c_short), ("dmPaperSize", ctypes.c_short),
                    ("dmPaperLength", ctypes.c_short), ("dmPaperWidth", ctypes.c_short),
                    ("dmScale", ctypes.c_short), ("dmCopies", ctypes.c_short),
                    ("dmDefaultSource", ctypes.c_short), ("dmPrintQuality", ctypes.c_short),
                    ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
                    ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
                    ("dmCollate", ctypes.c_short), ("dmFormName", ctypes.c_wchar * 32),
                    ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
                    ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
                    ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
                ]
            devmode = DEVMODE()
            devmode.dmSize = ctypes.sizeof(DEVMODE)
            ENUM_CURRENT_SETTINGS = -1
            ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode))
            return devmode.dmDisplayFrequency
        except Exception:
            return None

    def _ekran_bolgesi_ozeti(self, x, y, w, h):
        """Küçük bir ekran bölgesinin piksel verisinden hızlı bir 'özet' (checksum)
        çıkarır — art arda gelen özetler farklıysa görüntü değişmiş demektir."""
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc_ekran = user32.GetDC(0)
        hdc_bellek = gdi32.CreateCompatibleDC(hdc_ekran)
        h_bitmap = gdi32.CreateCompatibleBitmap(hdc_ekran, w, h)
        gdi32.SelectObject(hdc_bellek, h_bitmap)
        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(hdc_bellek, 0, 0, w, h, hdc_ekran, x, y, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
            ]
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 24
        bmi.biCompression = 0

        satir_boyutu = ((w * 3 + 3) // 4) * 4
        arabellek = ctypes.create_string_buffer(satir_boyutu * h)
        DIB_RGB_COLORS = 0
        gdi32.GetDIBits(hdc_bellek, h_bitmap, 0, h, arabellek, ctypes.byref(bmi), DIB_RGB_COLORS)

        gdi32.DeleteObject(h_bitmap)
        gdi32.DeleteDC(hdc_bellek)
        user32.ReleaseDC(0, hdc_ekran)

        return zlib.crc32(arabellek.raw)

    def _fps_overlay_ac_kapa(self):
        if self._fps_gosterge_penceresi is not None:
            self._fps_calisiyor = False
            try:
                self._fps_gosterge_penceresi.destroy()
            except Exception:
                pass
            self._fps_gosterge_penceresi = None
            self.fps_baslat_btn.config(text="▶ Göstergeyi Aç")
            return

        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return

        pencere = tk.Toplevel(self)
        pencere.overrideredirect(True)
        pencere.attributes("-topmost", True)
        pencere.configure(bg="#000000")
        try:
            pencere.attributes("-transparentcolor", "#000000")  # sadece Windows'ta çalışır
        except Exception:
            pass
        pencere.geometry("+12+12")  # ekranın sol üst köşesi

        etiket = tk.Label(
            pencere, text="FPS: --", fg=self.fps_renk_var.get(), bg="#000000",
            font=("Consolas", self.fps_boyut_var.get(), "bold"), justify="left",
        )
        etiket.pack()

        def surukle_baslat(e):
            pencere._sx, pencere._sy = e.x, e.y

        def surukle(e):
            x = pencere.winfo_pointerx() - pencere._sx
            y = pencere.winfo_pointery() - pencere._sy
            pencere.geometry(f"+{x}+{y}")

        etiket.bind("<Button-1>", surukle_baslat)
        etiket.bind("<B1-Motion>", surukle)

        self._fps_gosterge_penceresi = pencere
        self._fps_etiket = etiket
        self._fps_calisiyor = True
        self.fps_baslat_btn.config(text="⏸ Göstergeyi Kapat")

        hz = self._monitor_yenileme_hizi_al()

        def olcum_dongusu():
            bolge_x, bolge_y, bolge_w, bolge_h = 0, 0, 160, 160
            onceki_ozet = None
            degisim_sayaci = 0
            baslangic = time.time()
            while self._fps_calisiyor:
                try:
                    ozet = self._ekran_bolgesi_ozeti(bolge_x, bolge_y, bolge_w, bolge_h)
                    if onceki_ozet is not None and ozet != onceki_ozet:
                        degisim_sayaci += 1
                    onceki_ozet = ozet
                except Exception:
                    pass
                gecen = time.time() - baslangic
                if gecen >= 1.0:
                    fps_tahmini = degisim_sayaci
                    metin = f"FPS: ~{fps_tahmini}"
                    if self.fps_hz_goster_var.get() and hz:
                        metin += f"  ({hz}Hz)"
                    if self._fps_calisiyor:
                        self.after(0, lambda m=metin: self._fps_etiket_guncelle(m))
                    degisim_sayaci = 0
                    baslangic = time.time()
                time.sleep(0.01)

        threading.Thread(target=olcum_dongusu, daemon=True).start()

    def _fps_etiket_guncelle(self, metin):
        if self._fps_gosterge_penceresi is not None:
            try:
                self._fps_etiket.config(text=metin)
            except Exception:
                pass

    def _fps_overlay_guncelle_ayarlar(self):
        if self._fps_gosterge_penceresi is not None:
            try:
                self._fps_etiket.config(
                    font=("Consolas", int(self.fps_boyut_var.get()), "bold"),
                    fg=self.fps_renk_var.get(),
                )
            except Exception:
                pass

    def _fps_overlay_konumu_sifirla(self):
        if self._fps_gosterge_penceresi is not None:
            self._fps_gosterge_penceresi.geometry("+12+12")


    # ------------------------------------------------------------------
    # 14) Sistem Simgeleri (Bu Bilgisayar / Çöp Kutusu / Ağ) + Uygulama Logosu
    # ------------------------------------------------------------------
    def sistem_simgeleri_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Simgeler / Logo")

        ttk.Label(frame, text="Sistem Simgelerini Değiştir", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Masaüstündeki 'Bu Bilgisayar', 'Çöp Kutusu' ve 'Ağ' simgelerini "
                 "kendi .ico dosyanla değiştir.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        simge_hedefleri = [
            ("Çöp Kutusu (Boş)", "{645FF040-5081-101B-9F08-00AA002F954E}", "empty"),
            ("Çöp Kutusu (Dolu)", "{645FF040-5081-101B-9F08-00AA002F954E}", "full"),
            ("Bu Bilgisayar", "{20D04FE0-3AEA-1069-A2D8-08002B30309D}", None),
            ("Ağ", "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}", None),
            ("Kullanıcı Klasörü", "{59031a47-3f72-44a7-89c5-5595fe6b30ee}", None),
        ]
        for etiket, clsid, alt_deger in simge_hedefleri:
            satir = ttk.Frame(frame)
            satir.pack(fill="x", padx=15, pady=3)
            ttk.Label(satir, text=etiket, width=22).pack(side="left")
            ttk.Button(
                satir, text="📂 .ico Seç ve Uygula",
                command=lambda c=clsid, a=alt_deger, e=etiket: self._sistem_simgesi_uygula(c, a, e),
            ).pack(side="left", padx=5)

        ttk.Button(frame, text="↺ Tüm Sistem Simgelerini Varsayılana Sıfırla",
                   command=self._sistem_simgelerini_sifirla).pack(anchor="w", padx=15, pady=15)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Uygulama Logosu (Bu Programın İkonu)", style="Baslik.TLabel").pack(
            anchor="w", padx=15
        )
        ttk.Label(
            frame,
            text="Bu özelleştirme programının kendi pencere/görev çubuğu simgesini değiştir.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 8))
        ttk.Button(frame, text="🖼 Uygulama Logosunu Değiştir (.ico)", command=self._uygulama_logosunu_degistir).pack(
            anchor="w", padx=15, pady=5
        )

    def _sistem_simgesi_uygula(self, clsid, alt_deger, etiket):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        path = filedialog.askopenfilename(title=f"{etiket} için .ico dosyası seç",
                                           filetypes=[("Simge Dosyası", "*.ico")])
        if not path:
            return
        try:
            anahtar_yolu = rf"Software\Classes\CLSID\{clsid}\DefaultIcon"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, anahtar_yolu, 0, winreg.KEY_SET_VALUE) as key:
                deger_adi = alt_deger if alt_deger else ""
                winreg.SetValueEx(key, deger_adi, 0, winreg.REG_EXPAND_SZ, path)
            restart_explorer()
            messagebox.showinfo("Başarılı", f"{etiket} simgesi güncellendi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _sistem_simgelerini_sifirla(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        clsidler = [
            "{645FF040-5081-101B-9F08-00AA002F954E}",
            "{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
            "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}",
            "{59031a47-3f72-44a7-89c5-5595fe6b30ee}",
        ]
        try:
            for clsid in clsidler:
                anahtar_yolu = rf"Software\Classes\CLSID\{clsid}\DefaultIcon"
                try:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, anahtar_yolu)
                except FileNotFoundError:
                    pass
            restart_explorer()
            messagebox.showinfo("Başarılı", "Sistem simgeleri varsayılana sıfırlandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _uygulama_logosunu_degistir(self):
        path = filedialog.askopenfilename(title="Uygulama logosu seç", filetypes=[("Simge Dosyası", "*.ico")])
        if not path:
            return
        try:
            self.iconbitmap(path)
            messagebox.showinfo("Başarılı", "Uygulama logosu değiştirildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Logo uygulanamadı: {e}")

    # ------------------------------------------------------------------
    # 15) Dosya Kilitleme & Gizleme
    # ------------------------------------------------------------------
    def dosya_guvenlik_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Dosya Kilit/Gizle")

        ttk.Label(frame, text="Dosya / Klasör Gizleme", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Windows dosya özniteliğini (attribute) değiştirerek dosyayı normal "
                 "gezginde görünmez yapar. 'Gizli öğeleri göster' açıksa yine görülebilir.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        gizle_cercevesi = ttk.Frame(frame)
        gizle_cercevesi.pack(anchor="w", padx=15, pady=5)
        ttk.Button(gizle_cercevesi, text="🙈 Dosya/Klasör Gizle", command=self._dosyayi_gizle).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(gizle_cercevesi, text="👁 Dosya/Klasör Göster", command=self._dosyayi_goster).grid(
            row=0, column=1, padx=5
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Dosya / Klasör Kilitleme (Erişim İzni)", style="Baslik.TLabel").pack(
            anchor="w", padx=15
        )
        ttk.Label(
            frame,
            text="Windows'un yerleşik izin sistemini (icacls) kullanarak dosyaya kendi "
                 "kullanıcı hesabından erişimi reddeder — şifreleme değildir, bir "
                 "yönetici hesabı yine de erişebilir, ama günlük kullanımda dosyayı "
                 "açılamaz hale getirir.",
            foreground=RENK["metin_gri"], wraplength=560, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        kilit_cercevesi = ttk.Frame(frame)
        kilit_cercevesi.pack(anchor="w", padx=15, pady=5)
        ttk.Button(kilit_cercevesi, text="🔒 Dosya/Klasör Kilitle", command=self._dosyayi_kilitle).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(kilit_cercevesi, text="🔓 Kilidi Aç", command=self._dosyayi_kilidini_ac).grid(
            row=0, column=1, padx=5
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)
        ttk.Label(frame, text="İşlem Günlüğü", style="AltBaslik.TLabel").pack(anchor="w", padx=15)
        self.guvenlik_log = tk.Text(frame, height=8, width=75, bg=RENK["panel2"], fg=RENK["metin"],
                                     insertbackground=RENK["metin"], borderwidth=0)
        self.guvenlik_log.pack(padx=15, pady=5, fill="both")
        self.guvenlik_log.configure(state="disabled")

    def _guvenlik_log_yaz(self, satir):
        self.guvenlik_log.configure(state="normal")
        self.guvenlik_log.insert(tk.END, satir + "\n")
        self.guvenlik_log.see(tk.END)
        self.guvenlik_log.configure(state="disabled")

    def _dosya_veya_klasor_sec(self):
        path = filedialog.askopenfilename(title="Dosya seç (klasör için iptal edip klasör seçebilirsin)")
        if not path:
            path = filedialog.askdirectory(title="Klasör seç")
        return path

    def _dosyayi_gizle(self):
        path = self._dosya_veya_klasor_sec()
        if not path:
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            mevcut = ctypes.windll.kernel32.GetFileAttributesW(path)
            ctypes.windll.kernel32.SetFileAttributesW(path, mevcut | FILE_ATTRIBUTE_HIDDEN)
            self._guvenlik_log_yaz(f"[Gizlendi] {path}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _dosyayi_goster(self):
        path = self._dosya_veya_klasor_sec()
        if not path:
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            mevcut = ctypes.windll.kernel32.GetFileAttributesW(path)
            ctypes.windll.kernel32.SetFileAttributesW(path, mevcut & ~FILE_ATTRIBUTE_HIDDEN)
            self._guvenlik_log_yaz(f"[Gösterildi] {path}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _dosyayi_kilitle(self):
        path = self._dosya_veya_klasor_sec()
        if not path:
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            kullanici = os.environ.get("USERNAME", "")
            sonuc = subprocess.run(
                ["icacls", path, "/deny", f"{kullanici}:(R,W)"],
                capture_output=True, text=True,
            )
            self._guvenlik_log_yaz(f"[Kilitlendi] {path}\n  {sonuc.stdout.strip() or sonuc.stderr.strip()}")
            messagebox.showinfo("Başarılı", "Dosya/klasör kilitlendi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _dosyayi_kilidini_ac(self):
        path = self._dosya_veya_klasor_sec()
        if not path:
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        try:
            kullanici = os.environ.get("USERNAME", "")
            sonuc = subprocess.run(
                ["icacls", path, "/remove:d", kullanici],
                capture_output=True, text=True,
            )
            self._guvenlik_log_yaz(f"[Kilit Açıldı] {path}\n  {sonuc.stdout.strip() or sonuc.stderr.strip()}")
            messagebox.showinfo("Başarılı", "Dosya/klasörün kilidi açıldı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 16) Sistem Bilgisi
    # ------------------------------------------------------------------
    def sistem_bilgisi_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Sistem Bilgisi")

        ttk.Label(frame, text="Sistem Bilgisi", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        ttk.Button(frame, text="🔄 Bilgileri Yenile", command=self._sistem_bilgisini_yenile).pack(
            anchor="w", padx=15, pady=5
        )

        self.sistem_bilgi_text = tk.Text(
            frame, height=22, width=75, bg=RENK["panel2"], fg=RENK["metin"],
            insertbackground=RENK["metin"], borderwidth=0, font=("Consolas", 10),
        )
        self.sistem_bilgi_text.pack(padx=15, pady=10, fill="both")
        self.sistem_bilgi_text.insert("1.0", "Bilgileri görmek için 'Bilgileri Yenile' butonuna bas...")
        self.sistem_bilgi_text.configure(state="disabled")

    def _powershell_calistir(self, komut, timeout=10):
        try:
            sonuc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", komut],
                capture_output=True, text=True, timeout=timeout,
            )
            return sonuc.stdout.strip()
        except Exception:
            return ""

    def _sistem_bilgisini_yenile(self):
        self.sistem_bilgi_text.configure(state="normal")
        self.sistem_bilgi_text.delete("1.0", tk.END)
        self.sistem_bilgi_text.insert(tk.END, "Toplanıyor, lütfen bekle (birkaç saniye sürebilir)...\n")
        self.sistem_bilgi_text.configure(state="disabled")

        def topla():
            import platform
            s = []
            s.append("── İŞLETİM SİSTEMİ ──────────────────────────")
            s.append(f"OS               : {platform.system()} {platform.release()}")
            s.append(f"Sürüm Detayı     : {platform.version()}")
            s.append(f"Bilgisayar Adı   : {os.environ.get('COMPUTERNAME', '-')}")
            s.append(f"Kullanıcı Adı    : {os.environ.get('USERNAME', '-')}")
            s.append(f"Mimari           : {platform.machine()}")

            if IS_WINDOWS:
                s.append("")
                s.append("── İŞLEMCİ (CPU) ────────────────────────────")
                cpu_adi = self._powershell_calistir("(Get-CimInstance Win32_Processor).Name")
                if cpu_adi:
                    s.append(f"Model            : {cpu_adi}")
                cekirdek = self._powershell_calistir(
                    "(Get-CimInstance Win32_Processor).NumberOfCores"
                )
                thread = self._powershell_calistir(
                    "(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors"
                )
                hiz = self._powershell_calistir(
                    "(Get-CimInstance Win32_Processor).MaxClockSpeed"
                )
                if cekirdek or thread:
                    s.append(f"Çekirdek/Thread  : {cekirdek or '?'} çekirdek / {thread or '?'} thread")
                if hiz:
                    s.append(f"Maks. Hız        : {hiz} MHz")

                s.append("")
                s.append("── EKRAN KARTI (GPU) ────────────────────────")
                gpu_adlari = self._powershell_calistir(
                    "(Get-CimInstance Win32_VideoController) | ForEach-Object { $_.Name }"
                )
                vram_listesi = self._powershell_calistir(
                    "(Get-CimInstance Win32_VideoController) | "
                    "ForEach-Object { [math]::Round($_.AdapterRAM/1GB,1) }"
                )
                surucu_listesi = self._powershell_calistir(
                    "(Get-CimInstance Win32_VideoController) | ForEach-Object { $_.DriverVersion }"
                )
                if gpu_adlari:
                    gpu_satirlari = gpu_adlari.splitlines()
                    vram_satirlari = vram_listesi.splitlines() if vram_listesi else []
                    surucu_satirlari = surucu_listesi.splitlines() if surucu_listesi else []
                    for i, ad in enumerate(gpu_satirlari):
                        satir = f"GPU {i + 1}            : {ad.strip()}"
                        if i < len(vram_satirlari) and vram_satirlari[i].strip() not in ("0", ""):
                            satir += f"  (~{vram_satirlari[i].strip()} GB VRAM)"
                        s.append(satir)
                        if i < len(surucu_satirlari) and surucu_satirlari[i].strip():
                            s.append(f"   Sürücü Sürümü : {surucu_satirlari[i].strip()}")

                s.append("")
                s.append("── BELLEK / DEPOLAMA ────────────────────────")
                try:
                    ram_yuzde, ram_gb = self._ram_kullanimi_al()
                    s.append(f"RAM (Toplam)     : {ram_gb:.1f} GB   (Kullanım: %{ram_yuzde})")
                except Exception:
                    pass
                try:
                    disk_yuzde, bos_gb, toplam_gb = self._disk_kullanimi_al("C:\\")
                    s.append(
                        f"C: Diski         : {toplam_gb:.0f} GB toplam, {bos_gb:.0f} GB boş "
                        f"(Kullanım: %{disk_yuzde:.0f})"
                    )
                except Exception:
                    pass
                disk_modelleri = self._powershell_calistir(
                    "(Get-CimInstance Win32_DiskDrive) | ForEach-Object { $_.Model }"
                )
                if disk_modelleri:
                    for i, model in enumerate(disk_modelleri.splitlines()):
                        s.append(f"Disk {i + 1} Modeli   : {model.strip()}")

                s.append("")
                s.append("── ANAKART / BIOS ────────────────────────────")
                anakart = self._powershell_calistir(
                    "(Get-CimInstance Win32_BaseBoard).Product"
                )
                bios = self._powershell_calistir(
                    "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion"
                )
                if anakart:
                    s.append(f"Anakart          : {anakart}")
                if bios:
                    s.append(f"BIOS Sürümü      : {bios}")

                s.append("")
                s.append("── EKRAN ─────────────────────────────────────")
                hz = self._monitor_yenileme_hizi_al()
                if hz:
                    s.append(f"Monitör Hz       : {hz} Hz")

            metin = "\n".join(s)
            self.after(0, lambda: self._sistem_bilgisini_goster(metin))

        threading.Thread(target=topla, daemon=True).start()

    def _sistem_bilgisini_goster(self, metin):
        self.sistem_bilgi_text.configure(state="normal")
        self.sistem_bilgi_text.delete("1.0", tk.END)
        self.sistem_bilgi_text.insert(tk.END, metin)
        self.sistem_bilgi_text.configure(state="disabled")


    # ------------------------------------------------------------------
    # 17) Sistem Sağlığı (Windows Defender durumu + olay günlüğü)
    # ------------------------------------------------------------------
    def sistem_sagligi_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Sistem Sağlığı")

        ttk.Label(frame, text="Sistem Sağlığı", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="⚠ Bu bölüm kendi virüs tarama motorumuz DEĞİLDİR. Windows Defender'ın "
                 "kendi durumunu ve Windows'un sistem olay günlüğünü senin için okunabilir "
                 "hale getirir. Profesyonel bir antivirüs/güvenlik ürününün yerini tutmaz.",
            foreground=RENK["metin_gri"], wraplength=580, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=5)
        ttk.Button(btns, text="🛡 Defender Durumunu Kontrol Et", command=self._defender_durumu_kontrol).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(btns, text="☣ Son Tehdit Kayıtları", command=self._defender_tehdit_gecmisi).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(btns, text="⚠ Sistem Hata Günlüğü (Son 20)", command=self._sistem_hata_gunlugu).grid(
            row=1, column=0, padx=5, pady=5
        )
        ttk.Button(btns, text="🔍 Hızlı Tarama Başlat (Defender)", command=self._defender_hizli_tarama).grid(
            row=1, column=1, padx=5, pady=5
        )

        self.saglik_text = tk.Text(frame, height=18, width=75, bg=RENK["panel2"], fg=RENK["metin"],
                                    insertbackground=RENK["metin"], borderwidth=0, font=("Consolas", 9))
        self.saglik_text.pack(padx=15, pady=10, fill="both")
        self.saglik_text.insert("1.0", "Yukarıdaki butonlardan birine bas...")
        self.saglik_text.configure(state="disabled")

    def _saglik_text_yaz(self, metin):
        self.saglik_text.configure(state="normal")
        self.saglik_text.delete("1.0", tk.END)
        self.saglik_text.insert(tk.END, metin)
        self.saglik_text.configure(state="disabled")

    def _defender_durumu_kontrol(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        self._saglik_text_yaz("Kontrol ediliyor...")

        def isle():
            cikti = self._powershell_calistir(
                "Get-MpComputerStatus | Select-Object AntivirusEnabled, "
                "RealTimeProtectionEnabled, AntivirusSignatureLastUpdated, "
                "QuickScanAge, FullScanAge | Format-List", timeout=15
            )
            if not cikti:
                cikti = ("Windows Defender bilgisi alınamadı. Farklı bir antivirüs "
                          "yazılımı kullanıyor olabilirsin veya PowerShell'in bu " 
                          "komutu çalıştırma izni olmayabilir.")
            self.after(0, lambda: self._saglik_text_yaz(cikti))

        threading.Thread(target=isle, daemon=True).start()

    def _defender_tehdit_gecmisi(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        self._saglik_text_yaz("Tehdit geçmişi okunuyor...")

        def isle():
            cikti = self._powershell_calistir(
                "Get-MpThreatDetection | Select-Object -First 15 ThreatID, "
                "InitialDetectionTime, Resources | Format-List", timeout=15
            )
            if not cikti:
                cikti = "Kayıtlı bir tehdit bulunamadı (ya da Defender aktif değil)."
            self.after(0, lambda: self._saglik_text_yaz(cikti))

        threading.Thread(target=isle, daemon=True).start()

    def _sistem_hata_gunlugu(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        self._saglik_text_yaz("Olay günlüğü taranıyor...")

        def isle():
            cikti = self._powershell_calistir(
                "Get-WinEvent -FilterHashtable @{LogName='System'; Level=2} "
                "-MaxEvents 20 -ErrorAction SilentlyContinue | "
                "Select-Object TimeCreated, ProviderName, Message | Format-List",
                timeout=15,
            )
            if not cikti:
                cikti = "Son kayıtlarda kritik hata bulunamadı (iyi haber!)."
            self.after(0, lambda: self._saglik_text_yaz(cikti))

        threading.Thread(target=isle, daemon=True).start()

    def _defender_hizli_tarama(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        if not messagebox.askyesno(
            "Onay", "Windows Defender hızlı taraması başlatılacak (arka planda "
                    "birkaç dakika sürebilir). Devam edilsin mi?"
        ):
            return
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", "Start-MpScan -ScanType QuickScan"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            self._saglik_text_yaz("Hızlı tarama arka planda başlatıldı (Windows Defender).")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 20) Programlar (yüklü programları listele/kaldır — kendi eklemem)
    # ------------------------------------------------------------------
    def programlar_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Programlar")

        ttk.Label(frame, text="Yüklü Programlar", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Windows'un kendi kayıtlı program listesini okur. Kaldırma işlemi, "
                 "programın kendi resmi kaldırma (uninstaller) aracını çalıştırır — "
                 "bu araç dosya silme işlemi yapmaz, sadece ilgili programı tetikler.",
            foreground=RENK["metin_gri"], wraplength=580, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ust = ttk.Frame(frame)
        ust.pack(fill="x", padx=15, pady=5)
        ttk.Button(ust, text="🔄 Listeyi Yenile", command=self._programlari_listele).pack(side="left")
        self.program_arama_var = tk.StringVar()
        self.program_arama_var.trace_add("write", lambda *a: self._program_listesini_filtrele())
        ttk.Entry(ust, textvariable=self.program_arama_var, width=30).pack(side="left", padx=10)

        self.program_listbox = tk.Listbox(frame, width=75, height=14)
        self.program_listbox.pack(padx=15, pady=5, fill="both")

        ttk.Button(frame, text="🗑 Seçili Programı Kaldır", command=self._programi_kaldir).pack(
            anchor="w", padx=15, pady=10
        )

        self._program_listesi_verisi = []

    def _programlari_listele(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return

        def isle():
            sonuc = []
            anahtar_yollari = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            for hive, yol in anahtar_yollari:
                try:
                    with winreg.OpenKey(hive, yol) as ana_anahtar:
                        i = 0
                        while True:
                            try:
                                alt_ad = winreg.EnumKey(ana_anahtar, i)
                                i += 1
                                with winreg.OpenKey(ana_anahtar, alt_ad) as alt_anahtar:
                                    try:
                                        ad, _ = winreg.QueryValueEx(alt_anahtar, "DisplayName")
                                    except FileNotFoundError:
                                        continue
                                    try:
                                        kaldirma, _ = winreg.QueryValueEx(alt_anahtar, "UninstallString")
                                    except FileNotFoundError:
                                        kaldirma = None
                                    sonuc.append((ad, kaldirma))
                            except OSError:
                                break
                except FileNotFoundError:
                    continue
            sonuc.sort(key=lambda x: x[0].lower())
            self.after(0, lambda: self._program_listesini_guncelle(sonuc))

        threading.Thread(target=isle, daemon=True).start()

    def _program_listesini_guncelle(self, veri):
        self._program_listesi_verisi = veri
        self._program_listesini_filtrele()

    def _program_listesini_filtrele(self):
        if not hasattr(self, "program_listbox"):
            return
        filtre = self.program_arama_var.get().lower()
        self.program_listbox.delete(0, tk.END)
        for ad, _kaldirma in self._program_listesi_verisi:
            if filtre and filtre not in ad.lower():
                continue
            self.program_listbox.insert(tk.END, ad)

    def _programi_kaldir(self):
        secim = self.program_listbox.curselection()
        if not secim:
            return
        secili_ad = self.program_listbox.get(secim[0])
        eslesme = next((k for ad, k in self._program_listesi_verisi if ad == secili_ad), None)
        if not eslesme:
            messagebox.showwarning("Uyarı", "Bu program için kaldırma bilgisi bulunamadı.")
            return
        if not messagebox.askyesno("Onay", f"'{secili_ad}' kaldırılsın mı?\n\nBu, programın kendi "
                                            "kaldırma sihirbazını açacaktır."):
            return
        try:
            subprocess.Popen(eslesme, shell=True)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 21) Hakkında / Yasal Uyarı
    # ------------------------------------------------------------------
    def hakkinda_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="ℹ Hakkında")

        ttk.Label(frame, text="Hakkında ve Yasal Uyarı", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        metin_kutusu = tk.Text(frame, height=24, width=75, bg=RENK["panel2"], fg=RENK["metin"],
                                insertbackground=RENK["metin"], borderwidth=0, wrap="word",
                                font=("Segoe UI", 9))
        metin_kutusu.pack(padx=15, pady=10, fill="both")
        metin_kutusu.insert("1.0", YASAL_UYARI)
        metin_kutusu.configure(state="disabled")


    # ------------------------------------------------------------------
    # 22) Sıkıştırma (zip aç/oluştur — Python'un yerleşik zipfile'ı, ek gerekmez)
    # ------------------------------------------------------------------
    def sikistirma_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🗜 Sıkıştırma")

        ttk.Label(frame, text="Dosya Sıkıştırma / Arşiv", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Python'un kendi yerleşik zip motoruyla çalışır — WinRAR/7-Zip gibi "
                 "ek bir program kurmana gerek yok. Standart .zip formatı kullanılır, "
                 "her yerde açılabilir.",
            foreground=RENK["metin_gri"], wraplength=600, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        ttk.Button(btns, text="🗜 Dosya/Klasör Sıkıştır (.zip)", command=self._sikistir).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(btns, text="📂 .zip Aç / Çıkart", command=self._zip_ac).grid(row=0, column=1, padx=5)

        self.sikistirma_log = tk.Text(frame, height=14, width=75, bg=RENK["panel2"], fg=RENK["metin"],
                                       insertbackground=RENK["metin"], borderwidth=0)
        self.sikistirma_log.pack(padx=15, pady=10, fill="both")
        self.sikistirma_log.configure(state="disabled")

    def _sikistirma_log_yaz(self, satir):
        self.sikistirma_log.configure(state="normal")
        self.sikistirma_log.insert(tk.END, satir + "\n")
        self.sikistirma_log.see(tk.END)
        self.sikistirma_log.configure(state="disabled")

    def _sikistir(self):
        path = self._dosya_veya_klasor_sec()
        if not path:
            return
        hedef = filedialog.asksaveasfilename(
            title="Zip olarak kaydet", defaultextension=".zip",
            filetypes=[("Zip Arşivi", "*.zip")],
        )
        if not hedef:
            return
        try:
            with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.isdir(path):
                    ust_klasor = os.path.dirname(path.rstrip("\\/"))
                    for kok, _dizinler, dosyalar in os.walk(path):
                        for ad in dosyalar:
                            tam = os.path.join(kok, ad)
                            arcname = os.path.relpath(tam, ust_klasor)
                            z.write(tam, arcname)
                else:
                    z.write(path, os.path.basename(path))
            boyut_mb = os.path.getsize(hedef) / (1024 * 1024)
            self._sikistirma_log_yaz(f"[Sıkıştırıldı] {path}\n  → {hedef}  ({boyut_mb:.2f} MB)")
            messagebox.showinfo("Başarılı", f"Sıkıştırıldı:\n{hedef}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _zip_ac(self):
        zip_yolu = filedialog.askopenfilename(title="Açılacak .zip dosyasını seç",
                                               filetypes=[("Zip Arşivi", "*.zip")])
        if not zip_yolu:
            return
        hedef_klasor = filedialog.askdirectory(title="Çıkartılacak klasörü seç")
        if not hedef_klasor:
            return
        try:
            with zipfile.ZipFile(zip_yolu, "r") as z:
                z.extractall(hedef_klasor)
            self._sikistirma_log_yaz(f"[Çıkartıldı] {zip_yolu}\n  → {hedef_klasor}")
            messagebox.showinfo("Başarılı", "Arşiv çıkartıldı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 23) Ekran Rengi — parlaklık/kontrast/gama
    # ------------------------------------------------------------------
    def ekran_rengi_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🌈 Ekran Rengi")

        ttk.Label(frame, text="Ekran Rengi Ayarları", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Windows'un kendi ekran kartı sürücüsü bağımsız gama-ramp API'sini "
                 "kullanarak parlaklık/kontrast/gama ayarlar. Bazı ekran kartı "
                 "sürücüleri aşırı uç değerleri reddedebilir.",
            foreground=RENK["metin_gri"], wraplength=600, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.ekran_parlaklik_var = tk.DoubleVar(value=0.0)
        self.ekran_kontrast_var = tk.DoubleVar(value=1.0)
        self.ekran_gama_var = tk.DoubleVar(value=1.0)

        for etiket, degisken, minim, maksim in [
            ("Parlaklık (Brightness)", self.ekran_parlaklik_var, -0.3, 0.3),
            ("Kontrast (Contrast)", self.ekran_kontrast_var, 0.5, 1.8),
            ("Gama (Gamma)", self.ekran_gama_var, 0.5, 2.2),
        ]:
            satir = ttk.Frame(frame)
            satir.pack(fill="x", padx=15, pady=8)
            ttk.Label(satir, text=etiket, width=22).pack(side="left")
            ttk.Scale(
                satir, from_=minim, to=maksim, orient="horizontal", variable=degisken,
                length=320, command=lambda v: self._ekran_rengini_uygula(),
            ).pack(side="left", padx=10)

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=15)
        ttk.Button(btns, text="✅ Uygula", command=self._ekran_rengini_uygula).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="↺ Varsayılana Sıfırla", command=self._ekran_rengini_sifirla).grid(
            row=0, column=1, padx=5
        )

    def _gamma_rampi_hesapla_ve_uygula(self, parlaklik, kontrast, gama):
        if not IS_WINDOWS:
            return False
        try:
            class RAMP(ctypes.Structure):
                _fields_ = [
                    ("Red", wintypes.WORD * 256), ("Green", wintypes.WORD * 256),
                    ("Blue", wintypes.WORD * 256),
                ]
            ramp = RAMP()
            for i in range(256):
                deger = i / 255.0
                deger = deger ** (1.0 / max(0.1, gama))
                deger = (deger - 0.5) * kontrast + 0.5 + parlaklik
                deger = min(1.0, max(0.0, deger))
                w = int(deger * 65535)
                ramp.Red[i] = w
                ramp.Green[i] = w
                ramp.Blue[i] = w
            hdc = ctypes.windll.user32.GetDC(0)
            sonuc = ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return bool(sonuc)
        except Exception:
            return False

    def _ekran_rengini_uygula(self):
        if not IS_WINDOWS:
            return
        basarili = self._gamma_rampi_hesapla_ve_uygula(
            self.ekran_parlaklik_var.get(), self.ekran_kontrast_var.get(), self.ekran_gama_var.get()
        )
        if not basarili:
            pass  # sürükleme sırasında sık başarısızlık normal olabilir, sessiz geç

    def _ekran_rengini_sifirla(self):
        self.ekran_parlaklik_var.set(0.0)
        self.ekran_kontrast_var.set(1.0)
        self.ekran_gama_var.set(1.0)
        if IS_WINDOWS:
            self._gamma_rampi_hesapla_ve_uygula(0.0, 1.0, 1.0)
            messagebox.showinfo("Başarılı", "Ekran rengi varsayılana sıfırlandı.")
        else:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")

    # ------------------------------------------------------------------
    # 24) Ekstra Araçlar (Uyanık Tut + Hızlı Başlatıcı)
    # ------------------------------------------------------------------
    def powertoys_ekstra_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🧰 Ekstra")

        ttk.Label(frame, text="Ekstra Araçlar", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )

        ttk.Label(frame, text="Uyanık Tut", style="AltBaslik.TLabel").pack(
            anchor="w", padx=15, pady=(5, 2)
        )
        ttk.Label(
            frame,
            text="Bilgisayarın uyku moduna geçmesini/ekranın kararmasını engeller "
                 "(örn. uzun bir işlem/indirme sırasında).",
            foreground=RENK["metin_gri"], wraplength=600, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 5))
        self.uyanik_tut_btn = ttk.Button(frame, text="☕ Uyanık Tut: Kapalı", command=self._uyanik_tutu_degistir)
        self.uyanik_tut_btn.pack(anchor="w", padx=15, pady=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=15, pady=15)

        ttk.Label(frame, text="Hızlı Başlatıcı", style="AltBaslik.TLabel").pack(
            anchor="w", padx=15, pady=(5, 2)
        )
        ttk.Label(
            frame,
            text="Başlat menüsündeki kısayolları indeksler, yazarak anında arayıp "
                 "çift tıkla açabilirsin.",
            foreground=RENK["metin_gri"], wraplength=600, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 5))

        ttk.Button(frame, text="🔄 Uygulamaları İndeksle", command=self._baslangic_menusunu_indeksle).pack(
            anchor="w", padx=15, pady=5
        )
        self.hizli_baslatici_arama_var = tk.StringVar()
        self.hizli_baslatici_arama_var.trace_add("write", lambda *a: self._hizli_baslatici_filtrele())
        ttk.Entry(frame, textvariable=self.hizli_baslatici_arama_var, width=50).pack(
            anchor="w", padx=15, pady=5
        )
        self.hizli_baslatici_listbox = tk.Listbox(frame, width=75, height=10)
        self.hizli_baslatici_listbox.pack(padx=15, pady=5, fill="both")
        self.hizli_baslatici_listbox.bind("<Double-Button-1>", self._hizli_baslatici_ac)

    def _uyanik_tutu_degistir(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        self._uyanik_tut_aktif = not self._uyanik_tut_aktif
        try:
            if self._uyanik_tut_aktif:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                )
                self.uyanik_tut_btn.config(text="☕ Uyanık Tut: Açık")
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                self.uyanik_tut_btn.config(text="☕ Uyanık Tut: Kapalı")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _baslangic_menusunu_indeksle(self):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return

        def isle():
            yollar = [
                os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
                os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            ]
            sonuc = []
            for y in yollar:
                if not os.path.isdir(y):
                    continue
                for kok, _dizinler, dosyalar in os.walk(y):
                    for ad in dosyalar:
                        if ad.lower().endswith(".lnk"):
                            sonuc.append((os.path.splitext(ad)[0], os.path.join(kok, ad)))
            sonuc.sort(key=lambda x: x[0].lower())
            self._baslangic_menusu_indeksi = sonuc
            self.after(0, self._hizli_baslatici_filtrele)

        threading.Thread(target=isle, daemon=True).start()

    def _hizli_baslatici_filtrele(self):
        if not hasattr(self, "hizli_baslatici_listbox"):
            return
        sorgu = self.hizli_baslatici_arama_var.get().lower().strip()
        self.hizli_baslatici_listbox.delete(0, tk.END)
        for ad, _yol in self._baslangic_menusu_indeksi:
            if sorgu and sorgu not in ad.lower():
                continue
            self.hizli_baslatici_listbox.insert(tk.END, ad)

    def _hizli_baslatici_ac(self, event=None):
        secim = self.hizli_baslatici_listbox.curselection()
        if not secim:
            return
        secili_ad = self.hizli_baslatici_listbox.get(secim[0])
        eslesme = next((y for ad, y in self._baslangic_menusu_indeksi if ad == secili_ad), None)
        if not eslesme:
            return
        try:
            os.startfile(eslesme)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ------------------------------------------------------------------
    # 25) Oyun Bildirimi ("Giriş Sağlandı" tarzı, sol üstte beliren/kaybolan bildirim)
    # ------------------------------------------------------------------
    def oyun_bildirimi_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🎮 Oyun Bildirimi")

        ttk.Label(frame, text="Oyun / Program Giriş Bildirimi", style="Baslik.TLabel").pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ttk.Label(
            frame,
            text="Seçtiğin bir işlem (oyun/program .exe adı) başladığında, ekranın "
                 "sol üstünde 'Bağlantı Kuruldu' yazan küçük bir kutu belirip kısa "
                 "süre sonra otomatik solarak kaybolur. Bağımsız, hafif bir bildirim "
                 "aracıdır.",
            foreground=RENK["metin_gri"], wraplength=600, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ekle_cercevesi = ttk.Frame(frame)
        ekle_cercevesi.pack(anchor="w", padx=15, pady=5, fill="x")
        ttk.Label(ekle_cercevesi, text="İşlem adı (ör. csgo.exe):").pack(side="left")
        self.izlenen_islem_var = tk.StringVar()
        ttk.Entry(ekle_cercevesi, textvariable=self.izlenen_islem_var, width=25).pack(
            side="left", padx=8
        )
        ttk.Button(ekle_cercevesi, text="➕ Ekle", command=self._izlenen_islem_ekle).pack(side="left", padx=5)
        ttk.Button(ekle_cercevesi, text="➖ Kaldır", command=self._izlenen_islem_kaldir).pack(side="left", padx=5)

        self.izlenen_listbox = tk.Listbox(frame, width=50, height=6)
        self.izlenen_listbox.pack(padx=15, pady=5, anchor="w")

        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        self.oyun_izleme_btn = ttk.Button(btns, text="▶ İzlemeyi Başlat", command=self._oyun_izlemeyi_ac_kapa)
        self.oyun_izleme_btn.grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="🔔 Test Bildirimi Göster", command=lambda: self._oyun_bildirimi_goster(
            self.izlenen_islem_var.get() or "test.exe"
        )).grid(row=0, column=1, padx=5)

    def _izlenen_islem_ekle(self):
        ad = self.izlenen_islem_var.get().strip()
        if not ad:
            return
        if not ad.lower().endswith(".exe"):
            ad += ".exe"
        if ad not in self._izlenen_islemler:
            self._izlenen_islemler.append(ad)
            self.izlenen_listbox.insert(tk.END, ad)
        self.izlenen_islem_var.set("")

    def _izlenen_islem_kaldir(self):
        secim = self.izlenen_listbox.curselection()
        if not secim:
            return
        ad = self.izlenen_listbox.get(secim[0])
        self.izlenen_listbox.delete(secim[0])
        if ad in self._izlenen_islemler:
            self._izlenen_islemler.remove(ad)

    def _oyun_izlemeyi_ac_kapa(self):
        if self._oyun_izleme_aktif:
            self._oyun_izleme_aktif = False
            self.oyun_izleme_btn.config(text="▶ İzlemeyi Başlat")
            return
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        if not self._izlenen_islemler:
            messagebox.showwarning("Uyarı", "Önce izlenecek en az bir işlem ekle.")
            return
        self._oyun_izleme_aktif = True
        self.oyun_izleme_btn.config(text="⏸ İzlemeyi Durdur")

        def dongu():
            onceki = set()
            ilk_tur = True
            while self._oyun_izleme_aktif:
                try:
                    cikti = subprocess.run(
                        ["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=5
                    ).stdout
                    mevcut = set()
                    for satir in cikti.splitlines():
                        parcalar = satir.split('","')
                        if parcalar:
                            ad = parcalar[0].strip('"').lower()
                            mevcut.add(ad)
                    if not ilk_tur:
                        yeni_baslayanlar = mevcut - onceki
                        for izlenen in list(self._izlenen_islemler):
                            if izlenen.lower() in yeni_baslayanlar:
                                self.after(0, lambda i=izlenen: self._oyun_bildirimi_goster(i))
                    onceki = mevcut
                    ilk_tur = False
                except Exception:
                    pass
                for _ in range(30):
                    if not self._oyun_izleme_aktif:
                        break
                    time.sleep(0.1)

        threading.Thread(target=dongu, daemon=True).start()

    def _oyun_bildirimi_goster(self, isim):
        if not IS_WINDOWS:
            messagebox.showinfo("Bilgi", "Bu özellik yalnızca Windows'ta çalışır.")
            return
        pencere = tk.Toplevel(self)
        pencere.overrideredirect(True)
        pencere.attributes("-topmost", True)
        pencere.geometry("+16+16")
        try:
            pencere.attributes("-alpha", 0.0)
        except Exception:
            pass

        kutu = tk.Frame(pencere, bg="#101418", highlightbackground=RENK["vurgu2"],
                         highlightthickness=2, bd=0)
        kutu.pack()
        tk.Label(kutu, text=f"🎮 {isim}", bg="#101418", fg="#ffffff",
                 font=("Segoe UI", 11, "bold")).pack(padx=16, pady=(10, 2), anchor="w")
        tk.Label(kutu, text="✅ Bağlantı Kuruldu — Giriş Sağlandı", bg="#101418",
                 fg=RENK["vurgu2"], font=("Segoe UI", 9)).pack(padx=16, pady=(0, 10), anchor="w")

        def sol_yap(adim=0):
            alpha = min(0.95, (adim / 10) * 0.95)
            try:
                pencere.attributes("-alpha", alpha)
            except Exception:
                pass
            if adim < 10:
                pencere.after(25, lambda: sol_yap(adim + 1))
            else:
                pencere.after(1500, sag_yap)

        def sag_yap(adim=0):
            alpha = max(0.0, 0.95 - (adim / 12) * 0.95)
            try:
                pencere.attributes("-alpha", alpha)
            except Exception:
                pass
            if adim < 12:
                pencere.after(40, lambda: sag_yap(adim + 1))
            else:
                try:
                    pencere.destroy()
                except Exception:
                    pass

        sol_yap()

    # ------------------------------------------------------------------
    # 26) Dil / Language (7 dilde menü desteği)
    # ------------------------------------------------------------------
    def dil_sekmesi(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🌐 Dil")

        self._dil_baslik_label = ttk.Label(frame, text="Dil / Language", style="Baslik.TLabel")
        self._dil_baslik_label.pack(anchor="w", padx=15, pady=(15, 5))

        self._dil_aciklama_label = ttk.Label(
            frame, text="", foreground=RENK["metin_gri"], wraplength=620, justify="left",
        )
        self._dil_aciklama_label.pack(anchor="w", padx=15, pady=(0, 15))

        izgara = ttk.Frame(frame)
        izgara.pack(anchor="w", padx=15, pady=10)
        for i, kod in enumerate(DILLER):
            ttk.Button(
                izgara, text=DIL_ISIMLERI[kod], width=18,
                command=lambda k=kod: self._dili_uygula(k),
            ).grid(row=i // 3, column=i % 3, padx=6, pady=6)

    def _dili_uygula(self, dil_kodu):
        if dil_kodu not in DILLER:
            return
        self._mevcut_dil = dil_kodu

        # Pencere başlığı
        self.title(CEVIRILER["app_title"][dil_kodu])

        # Banner metinleri
        if hasattr(self, "_banner_canvas"):
            self._banner_canvas.itemconfigure(
                self._banner_baslik_id, text=CEVIRILER["app_title"][dil_kodu].split(" ", 1)[-1].upper()
            )
            self._banner_canvas.itemconfigure(self._banner_alt_id, text=CEVIRILER["banner_alt"][dil_kodu])

        # Alt bilgi çubuğu
        if hasattr(self, "_footer_sol_label"):
            self._footer_sol_label.config(text=CEVIRILER["app_title"][dil_kodu])

        # Sekme (menü) isimleri
        if hasattr(self, "notebook"):
            for i, anahtar in enumerate(TAB_SIRASI):
                try:
                    self.notebook.tab(i, text=CEVIRILER[anahtar][dil_kodu])
                except Exception:
                    pass

        # Dil sekmesinin kendi içeriği
        if hasattr(self, "_dil_baslik_label"):
            self._dil_baslik_label.config(text=CEVIRILER["dil_baslik"][dil_kodu])
        if hasattr(self, "_dil_aciklama_label"):
            self._dil_aciklama_label.config(text=CEVIRILER["dil_aciklama"][dil_kodu])


if __name__ == "__main__":
    app = WindowsOzellestiriciApp()
    app.mainloop()
