# Camera Controller - IoT & Embedded Systems

Sistem akses, tampilan, dan kontrol kamera (webcam) secara real-time menggunakan OpenCV dengan fitur Live Preview, Parameter Kamera, Key Mapping, dan Burst Capture.

## Fitur

- **Live Preview** — Tampilan kamera real-time dengan overlay informasi (resolusi, FPS, exposure, brightness, contrast)
- **Parameter Kamera** — Konfigurasi resolusi, shutter speed, ISO, brightness, contrast, saturation, dan sharpness
- **Key Mapping** — Kontrol penuh melalui tombol keyboard
- **Burst Capture** — Tangkapan gambar secara beruntun saat tombol ditekan
- **Fullscreen** — Mode layar penuh
- **JSON Config** — Konfigurasi tersimpan dalam file JSON yang dapat dimodifikasi

## Persyaratan

- Python 3.8+
- OpenCV (`opencv-python`)
- NumPy
- Webcam / kamera terhubung

## Instalasi

```bash
# Clone repository
git clone https://github.com/Gading20/IoT-Embedded-Systems.git
cd IoT-Embedded-Systems

# Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install opencv-python numpy
```

## Penggunaan

```bash
# Jalankan dengan config default
python3 camera_controller.py

# Jalankan dengan config custom
python3 camera_controller.py --config camera_config.json

# Override parameter via CLI
python3 camera_controller.py --width 1920 --height 1080 --fps 30

# Simpan config default ke file
python3 camera_controller.py --save-config
```

## Key Mapping

| Tombol | Fungsi |
|--------|--------|
| `SPACE` | Capture gambar |
| `B` | Toggle Burst Capture |
| `W` | Resolusi naik |
| `S` | Resolusi turun |
| `R` | Brightness naik |
| `E` | Brightness turun |
| `T` | Contrast naik |
| `D` | Contrast turun |
| `I` | Toggle Info Overlay |
| `F` | Toggle Fullscreen |
| `Q` / `ESC` | Keluar |

## Konfigurasi (`camera_config.json`)

```json
{
  "camera": {
    "device_id": 0,
    "width": 1280,
    "height": 720,
    "fps": 30,
    "shutter_speed": 0,
    "iso": 0,
    "auto_exposure": true,
    "brightness": 0,
    "contrast": 0,
    "saturation": 0,
    "sharpness": 0
  },
  "capture": {
    "output_dir": "captures",
    "filename_prefix": "capture",
    "burst_interval_ms": 100,
    "save_format": "png",
    "jpeg_quality": 95
  },
  "display": {
    "window_width": 1280,
    "window_height": 720,
    "show_info_overlay": true,
    "show_fps": true
  },
  "keybindings": {
    "capture": "SPACE",
    "burst_start": "b",
    "quit": "q",
    "toggle_info": "i",
    "toggle_fullscreen": "f",
    "resolution_up": "w",
    "resolution_down": "s",
    "brightness_up": "r",
    "brightness_down": "e",
    "contrast_up": "t",
    "contrast_down": "d"
  }
}
```

## Struktur Proyek

```
.
├── camera_controller.py    # Script utama
├── camera_config.json      # File konfigurasi
├── captures/               # Folder output gambar
└── venv/                   # Virtual environment
```

## Teknologi

- **OpenCV** — Library utama untuk akses kamera dan pemrosesan gambar
- **Video4Linux2 (V4L2)** — Backend akses kamera di Linux
- **NumPy** — Manipulasi array untuk efek visual

## Lisensi

MIT
