## Data Beats - Visualización Inteligente de Playlists y Análisis Descriptivo con Python

Taller dictado en la XXIX Reunión Científico del Grupo Argentino de Bioestadística.
**Profesores a Cargo del Taller**:
- Mg. Natalia Rubio - *Prof. Departamento de Estadística y Diplomada en Cs. de Datos, UNCo.*
- Prof. Sergio Ruminot - *Prof. Docente del Departamento de Estadística, UNCo.*
- Lic. Javier Molina - *Prof. Docente del Departamento de Estadística, UNCo.*

---

### Ideas de análisis para un dataset de Spotify

#### 📅 Análisis temporal
1. **¿Cuándo se agregan más canciones?**
   - Distribución por **año, mes, día de la semana o hora del día**.
   - Comparación entre fines de semana y días laborales (`is_weekend`).
   - ¿Existen **picos de actividad** en ciertos meses o años?

2. **Evolución del gusto musical**
   - Cambios en la **popularidad** de las canciones a lo largo del tiempo.
   - Cambios en la **duración promedio** de las canciones agregadas por año.

---

#### 🎶 Análisis de las canciones
3. **Duración de las canciones**
   - Distribución de `duration_minutes`.
   - Preferencias por canciones más **cortas o largas** según el año.

4. **Popularidad de las canciones**
   - ¿Se guardan canciones más **populares** o más **underground**?
   - Evolución del promedio de `popularity` con el tiempo.

5. **Explícito vs no explícito**
   - Porcentaje de canciones `explicit=True`.
   - Evolución de esta proporción con el tiempo o según el usuario que las agregó.

---

#### 👥 Análisis colaborativo (si hay varios usuarios `added_by`)
6. **¿Quién agrega más canciones?**
   - Ranking de usuarios que más aportan.
   - Preferencias de cada usuario según duración o popularidad.

7. **Patrones de agregación compartidos**
   - ¿Coincidencias en días u horarios de agregación?
   - ¿Ciertos usuarios tienden a agregar artistas similares?

---

#### 👨‍🎤 Artistas y álbumes
8. **Artistas más frecuentes**
   - Ranking de artistas en la playlist.
   - Evolución de la cantidad de canciones de cada artista a lo largo del tiempo.

9. **Álbumes representados**
   - ¿Qué álbumes dominan la playlist?
   - ¿Hay álbumes que se agregaron casi completos?

---

#### 🚀 Preguntas más avanzadas
10. **Recomendaciones basadas en gustos**
    - Identificación de **artistas emergentes** (baja popularidad pero recurrentes).
    - Patrones de agregado: ¿cuándo aparecen más canciones largas o poco populares?

11. **Visualizaciones interesantes**
    - Heatmap de canciones agregadas por **día de la semana vs hora**.
    - Línea de tiempo de la **popularidad promedio**.
    - Nube de palabras con artistas más frecuentes.