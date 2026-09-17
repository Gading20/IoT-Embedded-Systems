#!/usr/bin/env python3
"""
Camera Controller - IoT & Embedded Systems
===========================================
Script untuk mengakses, menampilkan, dan mengontrol kamera (webcam)
dengan fitur Live Preview, Parameter Kamera, Key Mapping, dan Burst Capture.

Requirements: opencv-python, numpy
Usage: python3 camera_controller.py [--config config.json]
"""

import cv2
import numpy as np
import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path


# =============================================================================
# KONFIGURASI DEFAULT
# =============================================================================
DEFAULT_CONFIG = {
    "camera": {
        "device_id": 0,
        "width": 1280,
        "height": 720,
        "fps": 30,
        "shutter_speed": 0,
        "iso": 0,
        "auto_exposure": True,
        "brightness": 0,
        "contrast": 0,
        "saturation": 0,
        "sharpness": 0,
    },
    "capture": {
        "output_dir": "captures",
        "filename_prefix": "capture",
        "burst_interval_ms": 100,
        "save_format": "png",
        "jpeg_quality": 95,
    },
    "display": {
        "window_width": 1280,
        "window_height": 720,
        "show_info_overlay": True,
        "show_fps": True,
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
        "contrast_down": "d",
    },
}


class CameraConfig:
    """Manajemen konfigurasi kamera dengan file JSON."""

    def __init__(self, config_path=None):
        self.config = DEFAULT_CONFIG.copy()
        self.config_path = config_path
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def load_config(self, path):
        """Load konfigurasi dari file JSON."""
        try:
            with open(path, "r") as f:
                user_config = json.load(f)
            self._deep_merge(self.config, user_config)
            print(f"[CONFIG] Konfigurasi dimuat dari: {path}")
        except Exception as e:
            print(f"[CONFIG] Error memuat config: {e}")

    def save_config(self, path=None):
        """Simpan konfigurasi ke file JSON."""
        path = path or self.config_path
        if not path:
            path = "camera_config.json"
        try:
            with open(path, "w") as f:
                json.dump(self.config, f, indent=2)
            print(f"[CONFIG] Konfigurasi disimpan ke: {path}")
        except Exception as e:
            print(f"[CONFIG] Error menyimpan config: {e}")

    def _deep_merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)

    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value


class CameraController:
    """Controller utama untuk mengakses dan mengontrol kamera."""

    RESOLUTION_PRESETS = [
        (640, 480, "VGA 480p"),
        (1280, 720, "HD 720p"),
        (1920, 1080, "Full HD 1080p"),
        (2560, 1440, "2K 1440p"),
        (3840, 2160, "4K 2160p"),
    ]

    def __init__(self, config: CameraConfig):
        self.config = config
        self.cap = None
        self.is_running = False
        self.is_burst = False
        self.show_overlay = config.get("display", "show_info_overlay", True)
        self.show_fps = config.get("display", "show_fps", True)
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        self.capture_count = 0
        self.burst_count = 0
        self.last_frame = None
        self.current_resolution_index = 1  # Default HD 720p
        self.fullscreen = False

        # Setup output directory
        output_dir = config.get("capture", "output_dir", "captures")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Inisialisasi kamera dengan parameter dari config."""
        device_id = self.config.get("camera", "device_id", 0)
        width = self.config.get("camera", "width", 1280)
        height = self.config.get("camera", "height", 720)
        fps = self.config.get("camera", "fps", 30)

        self.cap = cv2.VideoCapture(device_id, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(device_id)

        if not self.cap.isOpened():
            print("[ERROR] Tidak dapat mengakses kamera!")
            print("[INFO] Pastikan kamera terhubung dan tidak digunakan aplikasi lain.")
            return False

        # Set parameter kamera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        # V4L2 Camera Parameters
        if not self.config.get("camera", "auto_exposure", True):
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
            shutter_speed = self.config.get("camera", "shutter_speed", 0)
            if shutter_speed > 0:
                self.cap.set(cv2.CAP_PROP_EXPOSURE, shutter_speed)
            iso = self.config.get("camera", "iso", 0)
            if iso > 0:
                self.cap.set(cv2.CAP_PROP_GAIN, iso)
        else:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

        brightness = self.config.get("camera", "brightness", 0)
        if brightness != 0:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)

        contrast = self.config.get("camera", "contrast", 0)
        if contrast != 0:
            self.cap.set(cv2.CAP_PROP_CONTRAST, contrast)

        saturation = self.config.get("camera", "saturation", 0)
        if saturation != 0:
            self.cap.set(cv2.CAP_PROP_SATURATION, saturation)

        # Baca resolusi aktual
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[CAMERA] Kamera initialized: {actual_w}x{actual_h} @ {actual_fps:.1f} FPS")
        print(f"[CAMERA] Device ID: {device_id}")
        self.is_running = True
        return True

    def read_frame(self):
        """Baca frame dari kamera."""
        if not self.cap or not self.is_running:
            return None
        ret, frame = self.cap.read()
        if ret:
            self.last_frame = frame
            self._update_fps()
        return frame if ret else None

    def _update_fps(self):
        """Update counter FPS."""
        self.fps_counter += 1
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.current_fps = self.fps_counter / elapsed
            self.fps_counter = 0
            self.fps_start_time = time.time()

    def capture_image(self):
        """Capture satu gambar dan simpan ke file."""
        if self.last_frame is None:
            print("[CAPTURE] Tidak ada frame untuk di-capture")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        prefix = self.config.get("capture", "filename_prefix", "capture")
        fmt = self.config.get("capture", "save_format", "png")
        output_dir = self.config.get("capture", "output_dir", "captures")

        filename = f"{prefix}_{timestamp}.{fmt}"
        filepath = os.path.join(output_dir, filename)

        if fmt == "jpeg" or fmt == "jpg":
            quality = self.config.get("capture", "jpeg_quality", 95)
            cv2.imwrite(filepath, self.last_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        else:
            cv2.imwrite(filepath, self.last_frame)

        self.capture_count += 1
        print(f"[CAPTURE] #{self.capture_count} tersimpan: {filepath}")
        return filepath

    def burst_capture_start(self):
        """Mulai burst capture."""
        self.is_burst = True
        self.burst_count = 0
        print("[BURST] Burst capture dimulai...")

    def burst_capture_stop(self):
        """Hentikan burst capture."""
        self.is_burst = False
        print(f"[BURST] Burst capture selesai. Total: {self.burst_count} gambar")

    def burst_capture_tick(self):
        """Tick burst capture - panggil di setiap frame saat burst aktif."""
        if self.is_burst and self.last_frame is not None:
            self.capture_image()
            self.burst_count += 1

    def cycle_resolution(self, direction=1):
        """Ganti resolusi ke preset berikutnya/sebelumnya."""
        self.current_resolution_index = (
            self.current_resolution_index + direction
        ) % len(self.RESOLUTION_PRESETS)
        w, h, name = self.RESOLUTION_PRESETS[self.current_resolution_index]
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[RESOLUTION] {name}: {actual_w}x{actual_h}")

    def adjust_parameter(self, param, delta):
        """Ubah parameter kamera (brightness, contrast, dll)."""
        if param == "brightness":
            current = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, current + delta)
            print(f"[PARAM] Brightness: {current + delta}")
        elif param == "contrast":
            current = self.cap.get(cv2.CAP_PROP_CONTRAST)
            self.cap.set(cv2.CAP_PROP_CONTRAST, current + delta)
            print(f"[PARAM] Contrast: {current + delta}")

    def toggle_exposure_mode(self):
        """Toggle auto exposure vs manual."""
        current = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
        new_val = 0 if current == 1 else 1
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, new_val)
        mode = "Manual" if new_val == 0 else "Auto"
        print(f"[PARAM] Exposure Mode: {mode}")

    def release(self):
        """Release kamera."""
        self.is_running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def get_camera_info(self):
        """Ambil info kamera saat ini."""
        if not self.cap:
            return {}
        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "brightness": self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
            "contrast": self.cap.get(cv2.CAP_PROP_CONTRAST),
            "saturation": self.cap.get(cv2.CAP_PROP_SATURATION),
            "exposure": self.cap.get(cv2.CAP_PROP_EXPOSURE),
            "auto_exposure": self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE),
            "gain": self.cap.get(cv2.CAP_PROP_GAIN),
        }


class CameraGUI:
    """GUI untuk live preview dan kontrol kamera."""

    WINDOW_NAME = "Camera Controller - IoT Embedded Systems"

    def __init__(self, camera: CameraController, config: CameraConfig):
        self.camera = camera
        self.config = config
        self.window_width = config.get("display", "window_width", 1280)
        self.window_height = config.get("display", "window_height", 720)
        self.flash_effect = 0

    def _draw_overlay(self, frame):
        """Gambar informasi overlay di atas frame."""
        if not self.camera.show_overlay:
            return frame

        overlay = frame.copy()
        h, w = overlay.shape[:2]

        # Semi-transparent background untuk info
        panel_h = 120
        cv2.rectangle(overlay, (0, 0), (w, panel_h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        # Info kamera
        info = self.camera.get_camera_info()
        y_offset = 25
        line_height = 22

        text_color = (0, 255, 255)
        value_color = (255, 255, 255)

        # Baris 1: Resolusi & FPS
        cv2.putText(
            frame,
            f"RES: {info.get('width', 0)}x{info.get('height', 0)}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            text_color,
            1,
        )

        if self.camera.show_fps:
            fps_text = f"FPS: {self.camera.current_fps:.1f}"
            cv2.putText(
                frame,
                fps_text,
                (250, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0) if self.camera.current_fps > 15 else (0, 0, 255),
                1,
            )

        # Baris 2: Parameter
        y_offset += line_height
        exposure_mode = (
            "AUTO" if info.get("auto_exposure", 1) == 1 else "MANUAL"
        )
        cv2.putText(
            frame,
            f"EXPOSURE: {exposure_mode}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            text_color,
            1,
        )
        cv2.putText(
            frame,
            f"BRIGHT: {info.get('brightness', 0):.0f}",
            (250, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            text_color,
            1,
        )
        cv2.putText(
            frame,
            f"CONTRAST: {info.get('contrast', 0):.0f}",
            (450, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            text_color,
            1,
        )
        cv2.putText(
            frame,
            f"GAIN/ISO: {info.get('gain', 0):.0f}",
            (680, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            text_color,
            1,
        )

        # Baris 3: Status
        y_offset += line_height
        status_color = (0, 255, 0) if not self.camera.is_burst else (0, 0, 255)
        status_text = "REC" if self.camera.is_burst else "LIVE"
        cv2.putText(
            frame,
            f"[{status_text}]",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            status_color,
            2,
        )

        if self.camera.capture_count > 0:
            cv2.putText(
                frame,
                f"Captures: {self.camera.capture_count}",
                (120, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                value_color,
                1,
            )

        if self.camera.is_burst:
            cv2.putText(
                frame,
                f"Burst: {self.camera.burst_count}",
                (300, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
            )

        # Baris 4: Keybindings
        y_offset += line_height
        help_text = (
            "[SPACE] Capture | [B] Burst | [W/S] Resolution | "
            "[R/E] Brightness | [T/D] Contrast | [I] Info | [Q] Quit"
        )
        cv2.putText(
            frame, help_text, (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1,
        )

        return frame

    def _apply_flash(self, frame):
        """Efek flash saat capture."""
        if self.flash_effect > 0:
            white = np.ones_like(frame, dtype=np.uint8) * 255
            frame = cv2.addWeighted(
                white, self.flash_effect * 0.5, frame, 1 - self.flash_effect * 0.5, 0
            )
            self.flash_effect -= 0.1
        return frame

    def show_frame(self, frame):
        """Tampilkan frame dengan overlay."""
        frame = self._apply_flash(frame)
        frame = self._draw_overlay(frame)

        # Resize untuk display
        display_frame = cv2.resize(frame, (self.window_width, self.window_height))

        cv2.imshow(self.WINDOW_NAME, display_frame)

    def trigger_flash(self):
        """Trigger efek flash."""
        self.flash_effect = 1.0

    def get_key_from_event(self, key):
        """Konversi key event ke string key."""
        key_mappings = {
            32: "SPACE",
            113: "q",
            105: "i",
            98: "b",
            119: "w",
            115: "s",
            114: "r",
            101: "e",
            116: "t",
            100: "d",
            102: "f",
            27: "ESCAPE",
        }
        return key_mappings.get(key, chr(key) if 0 <= key < 256 else "UNKNOWN")


def load_config_from_args():
    """Parse argumen command line dan load config."""
    parser = argparse.ArgumentParser(
        description="Camera Controller - IoT Embedded Systems"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path ke file konfigurasi JSON"
    )
    parser.add_argument("--device", type=int, default=None, help="Camera device ID")
    parser.add_argument("--width", type=int, default=None, help="Resolusi lebar")
    parser.add_argument("--height", type=int, default=None, help="Resolusi tinggi")
    parser.add_argument("--fps", type=int, default=None, help="Target FPS")
    parser.add_argument(
        "--output", type=str, default=None, help="Output directory"
    )
    parser.add_argument(
        "--save-config", action="store_true", help="Simpan config default ke file"
    )
    args = parser.parse_args()

    if args.save_config:
        with open("camera_config.json", "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print("[CONFIG] Default config disimpan ke camera_config.json")
        sys.exit(0)

    config = CameraConfig(args.config)

    # Override dari command line
    if args.device is not None:
        config.set("camera", "device_id", args.device)
    if args.width is not None:
        config.set("camera", "width", args.width)
    if args.height is not None:
        config.set("camera", "height", args.height)
    if args.fps is not None:
        config.set("camera", "fps", args.fps)
    if args.output is not None:
        config.set("capture", "output_dir", args.output)

    return config


def print_banner():
    """Cetak banner startup."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          CAMERA CONTROLLER - IoT & Embedded Systems         ║
║                                                              ║
║  Fitur:                                                      ║
║  • Live Preview Real-time                                    ║
║  • Parameter Kamera (Resolusi, Exposure, ISO, Brightness)    ║
║  • Key Mapping untuk Capture                                 ║
║  • Burst Capture (Tahan tombol untuk continuous capture)     ║
║                                                              ║
║  Controls:                                                   ║
║  [SPACE]  Capture gambar     [B]    Toggle Burst Capture     ║
║  [W/S]    Ganti resolusi     [R/E]  Brightness +/-           ║
║  [T/D]    Contrast +/-       [I]    Toggle Info Overlay      ║
║  [F]      Toggle Fullscreen  [Q]    Quit                     ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Fungsi utama."""
    print_banner()

    # Load config
    config = load_config_from_args()

    # Inisialisasi kamera
    camera = CameraController(config)
    if not camera.initialize():
        print("[FATAL] Gagal menginisialisasi kamera. Keluar.")
        sys.exit(1)

    # Inisialisasi GUI
    gui = CameraGUI(camera, config)

    print("[SYSTEM] Tekan tombol di jendela kamera untuk kontrol.")
    print("[SYSTEM] Info overlay akan ditampilkan di bagian atas frame.\n")

    burst_interval = config.get("capture", "burst_interval_ms", 100) / 1000.0
    last_burst_time = 0

    try:
        while camera.is_running:
            frame = camera.read_frame()
            if frame is None:
                print("[WARNING] Gagal membaca frame. Mencoba ulang...")
                time.sleep(0.1)
                continue

            # Burst capture logic
            if camera.is_burst:
                current_time = time.time()
                if current_time - last_burst_time >= burst_interval:
                    camera.burst_capture_tick()
                    gui.trigger_flash()
                    last_burst_time = current_time

            # Tampilkan frame
            gui.show_frame(frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == 255:
                continue

            key_name = gui.get_key_from_event(key)
            keybindings = config.config.get("keybindings", {})

            if key_name == keybindings.get("quit", "q"):
                print("[SYSTEM] Keluar...")
                break

            elif key_name == keybindings.get("capture", "SPACE"):
                camera.capture_image()
                gui.trigger_flash()

            elif key_name == keybindings.get("burst_start", "b"):
                if camera.is_burst:
                    camera.burst_capture_stop()
                else:
                    camera.burst_capture_start()

            elif key_name == keybindings.get("resolution_up", "w"):
                camera.cycle_resolution(1)

            elif key_name == keybindings.get("resolution_down", "s"):
                camera.cycle_resolution(-1)

            elif key_name == keybindings.get("brightness_up", "r"):
                camera.adjust_parameter("brightness", 5)

            elif key_name == keybindings.get("brightness_down", "e"):
                camera.adjust_parameter("brightness", -5)

            elif key_name == keybindings.get("contrast_up", "t"):
                camera.adjust_parameter("contrast", 5)

            elif key_name == keybindings.get("contrast_down", "d"):
                camera.adjust_parameter("contrast", -5)

            elif key_name == keybindings.get("toggle_info", "i"):
                camera.show_overlay = not camera.show_overlay
                print(f"[SYSTEM] Overlay: {'ON' if camera.show_overlay else 'OFF'}")

            elif key_name == keybindings.get("toggle_fullscreen", "f"):
                gui.fullscreen = not gui.fullscreen
                if gui.fullscreen:
                    cv2.setWindowProperty(
                        gui.WINDOW_NAME,
                        cv2.WND_PROP_FULLSCREEN,
                        cv2.WINDOW_FULLSCREEN,
                    )
                else:
                    cv2.setWindowProperty(
                        gui.WINDOW_NAME,
                        cv2.WND_PROP_FULLSCREEN,
                        cv2.WINDOW_NORMAL,
                    )

            elif key_name == "ESCAPE":
                break

    except KeyboardInterrupt:
        print("\n[SYSTEM] Interrupted by user.")
    finally:
        # Stop burst jika masih aktif
        if camera.is_burst:
            camera.burst_capture_stop()

        camera.release()
        print(f"\n[SYSTEM] Total capture: {camera.capture_count}")
        print("[SYSTEM] Terima kasih telah menggunakan Camera Controller!")


if __name__ == "__main__":
    main()
