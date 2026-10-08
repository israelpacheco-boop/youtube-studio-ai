import os
import re
import streamlit as st
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Configuración de la interfaz de la página web
st.set_page_config(page_title="YouTube Studio AI", page_icon="🎬", layout="wide")

# Inicializa la API de OpenAI con tu clave configurada
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "sk-proj-psHtMyp23vBuiYE8Wa4RImNvpe7Iarhc5MNEqpc6Va1v5QZc5w3NL-8dkcJ8By8KBKqcVpZ2T3BlbkFJB8Cg6mBpxWc-1W0T82YV2WJtSBl6XU7uT1uD7-p5g-tA-4O3Y_3e_GqZkA"))

class YouTubeSkill:
    def __init__(self, url):
        self.url = url
        self.video_id = self.extract_video_id()
        self.video_title = "video_contenido"

    def extract_video_id(self):
        """Aísla de forma precisa el ID de 11 caracteres del video de YouTube."""
        regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        match = re.search(regex, self.url)
        if match:
            return match.group(1)
        return None

    def _format_time(self, seconds):
        """Convierte los segundos a marcas de tiempo legibles MM:SS o HH:MM:SS."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def fetch_video_title(self):
        """Consulta los metadatos de YouTube para extraer el título real."""
        ydl_opts = {
            'noplaylist': True,
            'cookies_from_browser': 'chrome',
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=False)
            self.video_title = info.get('title', 'video_contenido')
        return self.video_title

    def download_video(self, output_path="downloads"):
        """Descarga el video utilizando ordenamiento inteligente para asegurar compatibilidad MP4 nativa."""
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # Selección estándar flexible
            'format_sort': ['ext:mp4:m4a', 'codec:h264'],  # 👈 Prioriza MP4 y H264 pre-fusionados nativos de YouTube
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'noplaylist': True,
            'cookies_from_browser': 'chrome',
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=True)
            self.video_title = info.get('title', 'video_contenido')
        return self.video_title

    def download_audio(self, output_path="downloads"):
        """Extrae únicamente el flujo de audio del video en formato MP3."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'noplaylist': True,
            'cookies_from_browser': 'chrome',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=True)
            self.video_title = info.get('title', 'video_contenido')
        return self.video_title

    def get_transcript_and_summary(self, output_path="downloads"):
        """Extrae la transcripción con marcas de tiempo, genera el resumen con IA y guarda los .txt."""
        if not self.video_id:
            return None, "URL no válida."
        
        if self.video_title == "video_contenido":
            try:
                self.fetch_video_title()
            except:
                pass

        # Limpiar el título quitando caracteres especiales no permitidos en nombres de archivos de Windows
        clean_title = "".join([c for c in self.video_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()

        # 1. Obtener e indexar subtítulos de YouTube
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(self.video_id, languages=['es', 'en'])
            full_text_clean = " ".join([item['text'] for item in transcript_list])
            
            timed_lines = []
            for item in transcript_list:
                time_stamp = self._format_time(item['start'])
                timed_lines.append(f"[{time_stamp}] {item['text']}")
            full_text_timed = "\n".join(timed_lines)
            
            # 💾 Guardar archivo físico de la Transcripción Literal
            trans_file = os.path.join(output_path, f"Transcripcion - {clean_title}.txt")
            with open(trans_file, "w", encoding="utf-8") as f:
                f.write(full_text_timed)
                
        except Exception as e:
            return None, f"No se encontraron subtítulos automáticos en YouTube: {e}"

        # 2. Conectarse con OpenAI para procesar el resumen ejecutivo
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en resumir contenido audiovisual. Genera un resumen ejecutivo de alta calidad en español estructurado mediante títulos claros y viñetas con las ideas centrales."},
                    {"role": "user", "content": f"Resume la siguiente transcripción:\n\n{full_text_clean}"}
                ],
                temperature=0.4
            )
            resumen_ia = response.choices.message.content
            
            # 💾 Guardar archivo físico del Resumen Ejecutivo de IA
            resumen_file = os.path.join(output_path, f"Resumen - {clean_title}.txt")
            with open(resumen_file, "w", encoding="utf-8") as f:
                f.write(resumen_ia)
                
            return full_text_timed, resumen_ia
        except Exception as e:
            return full_text_timed, f"Error al generar el resumen con OpenAI pero transcripción guardada: {e}"

# --- RENDERING DE LA APLICACIÓN WEB INTERACTIVA (STREAMLIT) ---
st.title("🎬 YouTube Studio AI: Extractor & Transcriptor")
st.markdown("Genera descargas y transcripciones literales con marcas de tiempo usando la potencia de tu PC local.")

# Caja de entrada principal para el enlace
url_input = st.text_input("🔗 Introduce la URL del video de YouTube:", placeholder="https://www.youtube.com/watch?v=...")

if url_input:
    skill = YouTubeSkill(url_input)
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    # Creación de tres columnas simétricas para los botones de acción
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎥 Descargar Video MP4", use_container_width=True):
            with st.spinner("Descargando video..."):
                try:
                    titulo = skill.download_video()
                    st.success(f"✅ Video '{titulo}' guardado con éxito en la carpeta /downloads")
                except Exception as e:
                    st.error(f"Error al descargar el video: {e}")
                    
    with col2:
        if st.button("🎵 Descargar Audio MP3", use_container_width=True):
            with st.spinner("Descargando audio..."):
                try:
                    titulo = skill.download_audio()
                    st.success(f"✅ Audio '{titulo}' guardado con éxito en la carpeta /downloads")
                except Exception as e:
                    st.error(f"Error al descargar el audio: {e}")

    with col3:
        if st.button("📝 Obtener Transcripción y Resumen", use_container_width=True):
            with st.spinner("Procesando subtítulos e Inteligencia Artificial..."):
                transcripcion, resumen = skill.get_transcript_and_summary()
                
                if transcripcion:
                    st.success("✅ ¡Procesamiento completado! Informes de texto creados en /downloads")
                    
                    # Despliegue de paneles visuales
                    tab1, tab2 = st.tabs(["📋 Resumen con IA", "⏱️ Transcripción Literal"])
                    with tab1:
                        st.markdown(resumen)
                    with tab2:
                        st.text_area("Texto completo con marcas de tiempo:", value=transcripcion, height=400)
                else:
                    st.error(resumen)
