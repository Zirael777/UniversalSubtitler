import os
import subprocess
from engine.subtitler import SubtitlerEngine

def download_video(url):
    output_template = "%(title)s.%(ext)s"
    result = subprocess.run(
        ["yt-dlp", "-o", output_template, "--get-filename", url], 
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    filename = result.stdout.strip() if result.stdout else ""
    
    if not filename or "" in filename:
        ext_result = subprocess.run(
            ["yt-dlp", "--get-filename", "-o", "%(ext)s", url],
            check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        ext = ext_result.stdout.strip() if ext_result.stdout else "mp4"
        filename = f"downloaded_movie.{ext}"
        output_template = filename

    subprocess.run(["yt-dlp", "-o", output_template, url], check=True)
    return filename

def execute(intent, arguments, context=None):
    """Главная функция скилла для OpenClaw"""
    if intent == "create_subtitles":
        source = arguments.get("source")
        target_lang = arguments.get("to_lang", "ru") # По умолчанию переводим на русский
        
        if not source:
            return {"status": "error", "message": "Не указана ссылка или путь к видео."}
        
        try:
            # Скачивание, если передана ссылка
            if source.startswith("http"):
                file_path = download_video(source)
            else:
                file_path = source

            if not os.path.exists(file_path):
                return {"status": "error", "message": f"Файл {file_path} не найден."}

            # Инициализируем наш обновленный движок с поддержкой DeepL и улучшенными таймингами
            engine = SubtitlerEngine(model_size="small")
            
            base_name = os.path.splitext(file_path)[0]
            output_srt_orig = base_name + ".srt"
            output_srt_trans = f"{base_name}_{target_lang}.srt"

            # 1. Распознавание оригинальной речи с улучшенным разбиением фраз
            segments, detected_lang = engine.transcribe(file_path, language=None)
            
            # 2. Сохранение очищенного оригинала (например, итальянского)
            engine.save_as_srt(segments, output_srt_orig, translate_to=None)
            
            # 3. Перевод через ИИ DeepL на выбранный язык
            msg_appendix = ""
            if target_lang and detected_lang != target_lang:
                engine.save_as_srt(segments, output_srt_trans, translate_to=target_lang, original_lang=detected_lang)
                msg_appendix = f" и качественный перевод на '{target_lang}' (через DeepL: {output_srt_trans})"

            # Чистим временный звук
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")

            return {
                "status": "success",
                "message": f"Готово! Видео: {file_path}. Создан оригинал субтитров ({output_srt_orig}){msg_appendix}."
            }

        except Exception as e:
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")
            return {"status": "error", "message": f"Ошибка при обработке: {str(e)}"}

    return {"status": "error", "message": "Неизвестный интент."}
