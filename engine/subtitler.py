import ffmpeg
from faster_whisper import WhisperModel
import os
from deep_translator import GoogleTranslator # Переключились на сверхнадежный GoogleTranslator

class SubtitlerEngine:
    def __init__(self, model_size="small", device="cpu"):
        self.model = WhisperModel(model_size, device=device, compute_type="int8")

    def transcribe(self, input_path, language=None):
        audio_path = "temp_audio.wav"
        ffmpeg.input(input_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)
        
        print(f"[*] Запуск ИИ (Определение языка...) ...")
        
        # Улучшенные параметры разбивки: делаем фразы короче для кино-таймингов
        segments, info = self.model.transcribe(
            audio_path, 
            beam_size=5, 
            language=language,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=700),
            max_new_tokens=40 # Ограничиваем длину фразы, чтобы текст не слипался в минутные куски
        )
        
        print(f"[+] Обнаружен язык: {info.language} (вероятность: {info.language_probability:.2f})")
        print("[*] Начинаю распознавание текста...")
        
        processed_segments = []
        for segment in segments:
            print(f"[{self._format_time(segment.start)}]: {segment.text}")
            processed_segments.append(segment)
            
        return processed_segments, info.language

    def save_as_srt(self, segments, output_path, translate_to=None, original_lang="en"):
        """Сохраняет субтитры. Если нужно — делает качественный автоматический перевод."""
        
        # Безопасно обрезаем коды языков (из en-US делаем en)
        if original_lang:
            original_lang = original_lang[:2].lower()
        if translate_to:
            translate_to = translate_to[:2].lower()

        translator = None
        should_translate = False

        # Если целевой язык передан и он отличается от оригинала — включаем переводчик
        if translate_to and original_lang != translate_to:
            print(f"[*] Перевожу субтитры ('{original_lang}' -> '{translate_to}') через движок Google...")
            try:
                translator = GoogleTranslator(source=original_lang, target=translate_to)
                should_translate = True
            except Exception as e:
                print(f"[!] Ошибка инициализации переводчика: {e}. Сохраняю оригинал.")
                should_translate = False

        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments):
                start = self._format_time(segment.start)
                end = self._format_time(segment.end)
                
                text = segment.text.strip()
                
                # Игнорируем пустые строки или явные баги тишины Whisper
                if not text or (segment.end - segment.start) > 30: 
                    continue
                    
                # Переводим строку, если переводчик готов
                if should_translate and translator:
                    try:
                        text = translator.translate(text)
                    except Exception as e:
                        # Если одна строка сбоит (например, сетевой сбой), оставляем оригинал
                        pass
                
                f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")

    def _format_time(self, seconds):
        ms = int((seconds % 1) * 1000)
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
