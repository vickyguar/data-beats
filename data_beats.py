import time
import pandas as pd
from tqdm import tqdm

def get_all_playlist_tracks(sp, playlist_id):
    # Función para obtener TODAS las canciones de una playlist

    all_tracks = []
    offset = 0
    limit = 100  # Máximo por solicitud

    # Obtener info básica de la playlist
    playlist_info = sp.playlist(playlist_id, fields='name,tracks.total')
    playlist_name = playlist_info['name']
    total_tracks = playlist_info['tracks']['total']

    print(f"🎵 Playlist: {playlist_name}")
    print(f"📊 Total de canciones: {total_tracks}")
    print("⏳ Extrayendo todas las canciones...\n")

    # Extraer con paginación
    with tqdm(total=total_tracks, desc="Extrayendo") as pbar:
        while True:
            response = sp.playlist_items(
                playlist_id,
                fields='items.added_at,items.added_by.id,items.track.id,items.track.name,items.track.artists.name,items.track.album.name,items.track.duration_ms,items.track.popularity,items.track.explicit,items.track.disc_number,items.track.track_number',
                limit=limit,
                offset=offset
            )

            # Si no hay más canciones, terminar
            if not response['items']:
                break

            # Agregar a la lista
            all_tracks.extend(response['items'])
            pbar.update(len(response['items']))

            # Siguiente página
            offset += limit
            time.sleep(0.1)  # Pausa para evitar rate limiting

    print(f"✅ {len(all_tracks)} canciones extraídas exitosamente")
    
    return all_tracks, playlist_name


def create_df(all_tracks):
    data = []
    for item in tqdm(all_tracks, desc="Procesando datos"):
        # Verificar que la canción no sea None (a veces pasa)
        if item['track'] is None:
            continue

        track = item['track']

        # Procesar la fecha added_at
        added_at_str = item['added_at']
        added_at_dt = pd.to_datetime(added_at_str)

        data.append({
            # Información temporal
            'added_at_original': added_at_str,
            'added_date': added_at_dt.date(),
            'added_year': added_at_dt.year,
            'added_month': added_at_dt.month,
            'added_day': added_at_dt.day,
            'added_hour': added_at_dt.hour,
            'added_weekday': added_at_dt.day_name(),
            'added_month_name': added_at_dt.month_name(),
            'is_weekend': added_at_dt.weekday() >= 5,

            # Información de la canción
            'added_by': item['added_by']['id'] if item['added_by'] else 'Unknown',
            'track_id': track['id'],
            'title': track['name'],
            'artists': ', '.join([a['name'] for a in track['artists']]),
            'album': track['album']['name'],
            'duration_ms': track['duration_ms'],
            'duration_minutes': round(track['duration_ms'] / 60000, 2),
            'popularity': track['popularity'],
            'explicit': track['explicit'],
            'disc_number': track['disc_number'],
            'track_number': track['track_number']
        })

    # Crear DataFrame
    df = pd.DataFrame(data)

    print(f"🎉 DataFrame final creado")
    return df