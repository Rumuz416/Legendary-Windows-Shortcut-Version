```
Windows Özelleştirici (Windows Customizer)
--------------------------------------------
Linux'taki masaüstü özelleştirme araçlarına (GNOME Tweaks, KDE System Settings vb.)
benzer şekilde Windows için basit bir özelleştirme aracı.

Gereksinimler:
    - Sadece Windows üzerinde çalışır (winreg ve ctypes kullanır).
    - Python 3.8+
    - Ek paket gerekmez (sadece standart kütüphane).

Çalıştırma:
    python main.py

Not: Bazı ayarların etkili olması için Explorer'ın yeniden başlatılması
(veya oturumun kapatılıp açılması) gerekebilir. Program bunu otomatik dener.
```
⚡ Windows Customizer — Ultimate Edition
An advanced system customization toolkit developed using Python and Tkinter; it allows you to manage Windows system settings, theme preferences, the taskbar, mouse sensitivity, and performance options from a single dark-themed interface.

✨ Key Features
The application offers a wide range of controls across 15 different tabs:

🌙 Theme & Appearance: Dark/Light Mode switching and system accent color customization.

🖼 Background & Slideshow: Custom image loading (Fill, Fit, Stretch, Center, Span), solid color backgrounds, and timed automatic wallpaper slideshows.

🖱 Cursor Management: Built-in Windows cursor schemes (Black, Inverted, Large, etc.), cursor size, and Windows 11 cursor color customization.

🖥 Desktop & Taskbar: Show/hide desktop icons, transparency effects, and toggles for the search box and Task View button.

🚀 Performance Optimization: One-click switching between "Best Performance" (disabling visual effects) and "Best Appearance" modes.

📌 Startup Programs: List applications running at Windows startup (Registry Run key), and add or remove programs.

📋 Live Clipboard History: Capture text copied to the clipboard in the background, view history, and re-copy items.

🎯 Screen Color Picker: Capture the color of any point on the screen using an eyedropper tool and copy the HEX and RGB codes to the clipboard. 📐 Window Organizer: Align active windows to the left or right of the screen, keep windows always on top (Pin Topmost), and minimize all windows.

📊 Live System Monitor & Search: Real-time monitoring of RAM and disk space, and quick file search within the user directory.

⏱ Desktop Overlay & PrtScn: Transparent overlay window displaying FPS and time, plus a quick screenshot tool.

📋 Requirements
Operating System: Windows 10 / Windows 11 (Required for Windows Registry and Win32 API access)

Python Version: Python 3.8 or later
