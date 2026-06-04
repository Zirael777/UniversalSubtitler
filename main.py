import os
import sys
import argparse
import subprocess
import json
import urllib.request
from engine.subtitler import SubtitlerEngine

def get_user_country():
    """Автоматически определяет код страны пользователя по его IP"""
    try:
        url = "http://ip-api.com/json/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("countryCode", "UNKNOWN")
    except Exception:
        return "UNKNOWN"

def handle_input_source(source):
    # Шаг 1. Проверяем, является ли источник локальным файлом
    if os.path.exists(source) and os.path.isfile(source):
        print(f"[*] Обнаружен локальный файл: {source}")
        return source

    # Шаг 2. Если это ссылка, проверяем геопозицию
    is_youtube = "youtube.com" in source or "youtu.be" in source
    is_ru_platform = "rutube.ru" in source or "vk.com" in source

    if is_youtube or is_ru_platform:
        print("[*] Проверяю доступность платформы для вашего региона...")
        country = get_user_country()
        
        if is_youtube and country == "RU":
            print("\n" + "="*70)
            print("[!] Ошибка: В вашем регионе прямая загрузка с YouTube ограничена.")
            print("[*] Решение: Скачайте видеофайл самостоятельно (через VPN/браузер)")
            print("    и запустите скрипт, указав путь к файлу вместо ссылки.")
            print("    Пример: py main.py \"C:\\Downloads\\video.mp4\"")
            print("="*70 + "\n")
            sys.exit(1)
            
        if is_ru_platform and country != "RU" and country != "UNKNOWN":
            print("\n" + "="*70)
            print(f"[!] Ошибка: Вы находитесь в регионе ({country}).")
            print("[!] Прямая загрузка с ВК и Rutube за пределами РФ часто блокируется.")
            print("[*] Решение: Используйте российский VPN для работы со ссылкой")
            print("    или скачайте файл вручную и передайте локальный путь.")
            print("="*70 + "\n")
            sys.exit(1)

    # Шаг 3. Скачивание через чистый yt-dlp
    print(f"[*] Получаю информацию о видео и скачиваю по ссылке: {source}")
    output_template = "downloaded_movie.%(ext)s"
    
    cmd_download = [
        "yt-dlp", 
        "-o", output_template,
        "--no-playlist",
        "--merge-output-format", "mp4"
    ]
    
    if is_ru_platform:
        cmd_download.append("--no-proxy")
        
    cmd_download.append(source)
    
    try:
        print("[*] Запускаю скачивание через yt-dlp...")
        subprocess.run(cmd_download, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Ошибка при скачивании видео: {e}")
        sys.exit(1)
        
    for ext in ["mp4", "mkv", "webm"]:
        filename = f"downloaded_movie.{ext}"
        if os.path.exists(filename):
            return filename
        
    print("[!] Ошибка: Скачанный файл не найден!")
    sys.exit(1)

def process_media(source, language=None, target_lang="ru"):
    file_path = handle_input_source(source)
    
    print(f"[*] Файл готов к работе: {file_path}")
    print("[*] Запускаю извлечение аудио и генерацию субтитров через Whisper...")
    
    try:
        engine = SubtitlerEngine(model_size="small")
        base_name = os.path.splitext(file_path)[0]
        output_srt_orig = base_name + ".srt"
        output_srt_trans = f"{base_name}_{target_lang}.srt"

        # 1. Распознавание оригинала
        segments, detected_lang = engine.transcribe(file_path, language=language)
        
        # 2. Сохранение оригинала
        engine.save_as_srt(segments, output_srt_orig, translate_to=None)
        print(f"[+] Создан оригинальный файл субтитров: {output_srt_orig}")
        
        # 3. Перевод (если целевой язык отличается)
        if target_lang and detected_lang != target_lang:
            engine.save_as_srt(segments, output_srt_trans, translate_to=target_lang, original_lang=detected_lang)
            print(f"[+] Создан переведенный файл субтитров ({target_lang}): {output_srt_trans}")

    except Exception as e:
        print(f"[!] Ошибка при обработке ИИ: {e}")
    finally:
        if os.path.exists("temp_audio.wav"):
            os.remove("temp_audio.wav")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Subtitler")
    parser.add_argument("source", help="Ссылка на видео (ВК/Рутуб/YouTube) или путь к локальному файлу")
    parser.add_argument("--lang", help="Исходный язык видео", default=None)
    parser.add_argument("--to-lang", help="Язык перевода субтитров (по умолчанию ru)", default="ru")
    
    args = parser.parse_args()
    process_media(args.source, language=args.lang, target_lang=args.to_lang)
