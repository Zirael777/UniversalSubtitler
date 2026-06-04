import os
import sys
import subprocess
import json
import urllib.request
from engine.subtitler import SubtitlerEngine

def get_user_country():
    try:
        url = "http://ip-api.com/json/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("countryCode", "UNKNOWN")
    except Exception:
        return "UNKNOWN"

def download_video_for_skill(source):
    if os.path.exists(source) and os.path.isfile(source):
        return source

    is_youtube = "youtube.com" in source or "youtu.be" in source
    is_ru_platform = "rutube.ru" in source or "vk.com" in source

    if is_youtube or is_ru_platform:
        country = get_user_country()
        if is_youtube and country == "RU":
            raise Exception("В вашем регионе прямая загрузка с YouTube ограничена. Пожалуйста, укажите локальный путь к предварительно скачанному файлу.")
        if is_ru_platform and country != "RU" and country != "UNKNOWN":
            raise Exception(f"Вы находитесь в регионе {country}. Загрузка с ВК/Rutube заблокирована платформой. Используйте локальный файл.")

    output_template = "downloaded_movie.%(ext)s"
    cmd_download = ["yt-dlp", "-o", output_template, "--no-playlist", "--merge-output-format", "mp4"]
    
    if is_ru_platform:
        cmd_download.append("--no-proxy")
    cmd_download.append(source)
    
    subprocess.run(cmd_download, check=True)
    
    for ext in ["mp4", "mkv", "webm"]:
        filename = f"downloaded_movie.{ext}"
        if os.path.exists(filename):
            return filename
    raise FileNotFoundError("Скачанный файл не найден.")

def execute(intent, arguments, context=None):
    if intent == "create_subtitles":
        source = arguments.get("source")
        target_lang = arguments.get("to_lang", "ru")
        
        if not source:
            return {"status": "error", "message": "Не указана ссылка или путь к видео."}
        
        try:
            file_path = download_video_for_skill(source)

            engine = SubtitlerEngine(model_size="small")
            base_name = os.path.splitext(file_path)[0]
            output_srt_orig = base_name + ".srt"
            output_srt_trans = f"{base_name}_{target_lang}.srt"

            # 1. Распознавание оригинала
            segments, detected_lang = engine.transcribe(file_path, language=None)
            
            # 2. Сохранение оригинала
            engine.save_as_srt(segments, output_srt_orig, translate_to=None)
            
            # 3. Перевод через GoogleTranslator
            msg_appendix = ""
            if target_lang and detected_lang != target_lang:
                engine.save_as_srt(segments, output_srt_trans, translate_to=target_lang, original_lang=detected_lang)
                msg_appendix = f" и перевод на '{target_lang}' ({output_srt_trans})"

            return {
                "status": "success",
                "message": f"Готово! Создан оригинал субтитров ({output_srt_orig}){msg_appendix}."
            }

        except Exception as e:
            return {"status": "error", "message": f"Ошибка при обработке: {str(e)}"}
        finally:
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")

    return {"status": "error", "message": "Неизвестный интент."}
