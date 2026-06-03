import os
import argparse
import subprocess
from engine.subtitler import SubtitlerEngine

def cleanup():
    # Удаляем только временный аудиофайл, чтобы не засорять диск.
    # Видеофайл теперь НЕ удаляем, так как он сохраняется под своим настоящим именем для просмотра.
    if os.path.exists("temp_audio.wav"): 
        os.remove("temp_audio.wav")

def download_video(url):
    print(f"[*] Получаю информацию о видео и скачиваю: {url}")
    
    # Шаблон имени файла: оригинальное название.расширение
    output_template = "%(title)s.%(ext)s"
    
    # Запрашиваем имя файла. 
    # Добавляем errors="replace", чтобы скрипт никогда не падал из-за кодировок в Windows
    result = subprocess.run(
        ["yt-dlp", "-o", output_template, "--get-filename", url], 
        check=True, 
        capture_output=True, 
        text=True,
        encoding="utf-8",
        errors="replace"  # Заменяет кривые символы, если utf-8 сбоит в консоли
    )
    
    # Очищаем имя от лишних пробелов и переносов строки
    filename = result.stdout.strip() if result.stdout else ""
    
    # Если из-за специфики терминала имя прочитать не удалось, даем резервное имя,
    # чтобы не падать с ошибкой AttributeError
    if not filename or "" in filename:
        print("[!] Внимание: Обнаружены проблемы с кодировкой названия. Использую резервное имя файла.")
        # Запрашиваем только расширение, чтобы знать во что качать (mp4/mkv)
        ext_result = subprocess.run(
            ["yt-dlp", "--get-filename", "-o", "%(ext)s", url],
            check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        ext = ext_result.stdout.strip() if ext_result.stdout else "mp4"
        filename = f"downloaded_movie.{ext}"
        output_template = filename

    # Скачиваем сам фильм под полученным именем
    subprocess.run(["yt-dlp", "-o", output_template, url], check=True)
    
    return filename

def process_media(source, model_size="small", language=None, target_lang="ru"):
    if source.startswith("http"):
        file_path = download_video(source)
    else:
        file_path = source

    if not os.path.exists(file_path):
        print(f"Ошибка: Файл {file_path} не найден.")
        return

    engine = SubtitlerEngine(model_size=model_size)
    
    # Получаем имя файла без расширения (например, "Красивое название фильма")
    base_name = os.path.splitext(file_path)[0]
    output_srt_orig = base_name + ".srt"
    output_srt_trans = f"{base_name}_{target_lang}.srt"
    
    print(f"[*] Обработка файла: {file_path}")
    try:
        # 1. Распознаем оригинальную речь
        segments, detected_lang = engine.transcribe(file_path, language=language)
        
        # 2. Сохраняем оригинал под именем фильма (например, "Название_фильма.srt")
        print(f"[*] Сохраняю оригинальные субтитры ({detected_lang})...")
        engine.save_as_srt(segments, output_srt_orig, translate_to=None)
        print(f"[+] Оригинал сохранен в: {output_srt_orig}")
        
        # 3. Переводим на язык, выбранный пользователем (например, "Название_фильма_ru.srt")
        if target_lang and detected_lang != target_lang:
            engine.save_as_srt(segments, output_srt_trans, translate_to=target_lang, original_lang=detected_lang)
            print(f"[+] Перевод на '{target_lang}' сохранен в: {output_srt_trans}")
            
    except Exception as e:
        print(f"[!] Ошибка: {e}")
    finally:
        cleanup()
        print("[*] Временные файлы очищены.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Ссылка на видео (VK/YouTube) или путь к файлу")
    parser.add_argument("--lang", default=None, help="Язык оригинала видео (по умолчанию: автоопределение)")
    parser.add_argument("--to_lang", default="ru", help="Язык перевода субтитров (по умолчанию: ru)")
    args = parser.parse_args()
    
    process_media(args.source, language=args.lang, target_lang=args.to_lang)