import os
import re
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Configuración de la interfaz en la nube
st.set_page_config(page_title="YouTube AI Workspace", page_icon="📝", layout="wide")

# Inicializa la API de OpenAI leyendo los Secrets configurados en la nube
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class YouTubeCloudSkill:
    def __init__(self, url):
        self.url = url
        self.video_id = self.extract_video_id()

    def extract_video_id(self):
        """Aísla el ID de 11 caracteres del video de YouTube de forma segura."""
        regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        match = re.search(regex, self.url)
        if match:
            return match.group(1)
        return None

    def _format_time(self, seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def get_transcript_and_summary(self):
        if not self.video_id:
            return None, "URL de YouTube no válida."

        # 1. Obtener subtítulos de la API pública sin necesidad de simular navegadores
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(self.video_id, languages=['es', 'en'])
            full_text_clean = " ".join([item['text'] for item in transcript_list])
            
            timed_lines = []
            for item in transcript_list:
                time_stamp = self._format_time(item['start'])
                timed_lines.append(f"[{time_stamp}] {item['text']}")
            full_text_timed = "\n".join(timed_lines)
        except Exception as e:
            return None, f"No se pudieron extraer los subtítulos automáticos: {e}. Verifique que el video contenga pistas de subtítulos disponibles en la plataforma."

        # 2. Conexión directa a OpenAI para procesar el resumen ejecutivo
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
            return full_text_timed, resumen_ia
        except Exception as e:
            return full_text_timed, f"Error en el motor de Inteligencia Artificial (OpenAI): {e}"

# --- DISEÑO CLOUD EN PANTALLA ---
st.title("🎬 YouTube Studio AI: Transcriptor & Resumidor")
st.markdown("Analiza videos educativos o cursos en internet de manera instantánea mediante Inteligencia Artificial.")

url_input = st.text_input("🔗 Introduce la URL del video de YouTube:", placeholder="https://www.youtube.com/watch?v=...")

if url_input:
    skill = YouTubeCloudSkill(url_input)
    
    if st.button("🚀 Procesar Video con Inteligencia Artificial", use_container_width=True):
        with st.spinner("Conectando con servidores de YouTube y OpenAI..."):
            transcripcion, resumen = skill.get_transcript_and_summary()
            
            if transcripcion:
                st.success("✅ ¡Análisis completado de forma exitosa!")
                
                # Despliegue de paneles visuales nativos
                tab1, tab2 = st.tabs(["📋 Resumen Ejecutivo", "⏱️ Transcripción Literal"])
                with tab1:
                    st.markdown(resumen)
                with tab2:
                    st.text_area("Texto completo indexado con marcas de tiempo:", value=transcripcion, height=450)
            else:
                st.error(resumen)
