from typing import Dict, List, Tuple, Any
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from tqdm import tqdm
from spotipy import Spotify


def get_all_playlist_tracks(sp: Spotify, playlist_id: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Obtener todas las canciones de una playlist de Spotify.
    
    Obtiene datos completos de la playlist respetando límites de la API.
    
    Args:
        sp: instancia del cliente Spotify autenticada.
        playlist_id: el ID de la playlist de Spotify.
        
    Returns:
        Tupla que contiene:
        - lista de items de canciones con metadatos.
        - nombre de la playlist.
    """
    all_tracks = []
    offset = 0
    limit = 100  # máximo por solicitud

    # obtener info básica de la playlist
    playlist_info = sp.playlist(playlist_id, fields='name,tracks.total')
    playlist_name = playlist_info['name']
    total_tracks = playlist_info['tracks']['total']

    print(f"Playlist: {playlist_name}")
    print(f"Total de canciones: {total_tracks}")
    print("Extrayendo todas las canciones...\n")

    # extraer con paginación
    with tqdm(total=total_tracks, desc="Extrayendo") as pbar:
        while True:
            response = sp.playlist_items(
                playlist_id,
                fields='items.added_at,items.added_by.id,items.track.id,items.track.name,items.track.artists.name,items.track.album.name,items.track.duration_ms,items.track.popularity,items.track.explicit,items.track.disc_number,items.track.track_number',
                limit=limit,
                offset=offset
            )

            # si no hay más canciones, terminar
            if not response['items']:
                break

            # agregar a la lista
            all_tracks.extend(response['items'])
            pbar.update(len(response['items']))

            # siguiente página
            offset += limit
            time.sleep(0.1)  # pausa para evitar rate limiting

    print(f"Se extrajeron exitosamente {len(all_tracks)} canciones")
    
    return all_tracks, playlist_name


def create_df(all_tracks: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Transformar datos crudos de canciones de Spotify en un DataFrame.
    
    Args:
        all_tracks: lista de items de canciones de la API de Spotify.
        
    Returns:
        DataFrame con información procesada de canciones y características temporales.
    """
    data = []
    for item in tqdm(all_tracks, desc="Procesando datos"):
        # verificar que la canción no sea None (a veces pasa)
        if item['track'] is None:
            continue

        track = item['track']

        # procesar datetime added_at
        added_at_str = item['added_at']
        added_at_dt = pd.to_datetime(added_at_str)

        data.append({
            # info temporal
            'added_at_original': added_at_str,
            'added_date': added_at_dt.date(),
            'added_year': added_at_dt.year,
            'added_month': added_at_dt.month,
            'added_day': added_at_dt.day,
            'added_hour': added_at_dt.hour,
            'added_weekday': added_at_dt.day_name(),
            'added_month_name': added_at_dt.month_name(),
            'is_weekend': added_at_dt.weekday() >= 5,

            # info de la canción
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

    # crear DataFrame
    df = pd.DataFrame(data)

    print("DataFrame creado exitosamente")
    
    return df


def get_user_public_playlists(sp: Spotify, user_id: str) -> Tuple[pd.DataFrame, str]:
    """
    Obtener todas las playlists PÚBLICAS!! de un usuario de Spotify.
    
    Args:
        sp: instancia del cliente Spotify autenticada.
        user_id: el ID del usuario de Spotify.
        
    Returns:
        Tupla que contiene:
        - dataFrame con información de playlists (ID, nombre, cantidad de canciones, propietario).
        - nombre de usuario.
    """
    user_info = sp.user(user_id)
    username = user_info.get('display_name', user_id)

    print(f"Usuario: {username}")
    print("Extrayendo playlists públicas...\n")

    playlists = []
    offset = 0
    limit = 50

    # primera llamada para saber el total
    first_response = sp.user_playlists(user_id, limit=limit, offset=offset)
    total_playlists = first_response['total']
    playlists.extend(first_response['items'])

    with tqdm(total=total_playlists, desc="Playlists") as pbar:
        pbar.update(len(first_response['items']))

        while first_response['next'] is not None:
            offset += limit
            response = sp.user_playlists(user_id, limit=limit, offset=offset)
            playlists.extend(response['items'])
            pbar.update(len(response['items']))
            time.sleep(0.1)  # evitar rate limit
            first_response = response
    
    data = []

    for p in playlists:
        if p['public']:
            data.append({
                'playlist_id': p['id'],
                'playlist_name': p['name'],
                'tracks_total': p['tracks']['total'],
                'owner_id': p['owner']['id']
            })

    df_playlists = pd.DataFrame(data)

    print(f"Se extrajeron exitosamente {len(df_playlists)} playlists públicas")

    return df_playlists, username


def recommend_from_artists(sp: Spotify, df_user_tracks: pd.DataFrame, limit_per_artist: int = 2, max_artists: int = 5) -> pd.DataFrame:
    """
    Generar recomendaciones de canciones basadas en los principales artistas del usuario.

    Args:
        sp: instancia del cliente Spotify autenticada.
        df_user_tracks: DataFrame que contiene el historial de canciones del usuario.
        limit_per_artist: cantidad máxima de recomendaciones por artista.
        max_artists: cantidad de principales artistas a considerar para recomendaciones.
        
    Returns:
        DataFrame con canciones recomendadas (ID, título, artistas, popularidad).
    """
    listened_tracks = set(df_user_tracks["track_id"].dropna())

    top_artists = (
        df_user_tracks["artists"]
        .value_counts()
        .head(max_artists)
        .index
        .tolist()
    )

    recommendations = []

    for artist_name in top_artists:
        res = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        if not res["artists"]["items"]:
            continue

        artist_id = res["artists"]["items"][0]["id"]

        try:
            #user_country = sp.current_user()["country"]
            top_tracks = sp.artist_top_tracks(artist_id, country='AR')["tracks"]
        except:
            continue

        added_for_artist = 0

        for t in top_tracks:
            if t["id"] in listened_tracks:
                continue

            recommendations.append({
                "track_id": t["id"],
                "title": t["name"],
                "artists": ", ".join(a["name"] for a in t["artists"]),
                "popularity": t["popularity"],
            })

            added_for_artist += 1

            if added_for_artist >= limit_per_artist:
                break
    df_recs = pd.DataFrame(recommendations)

    return (
        df_recs
        .drop_duplicates("track_id")
        .head(20)
        .reset_index(drop=True)
    )


def analyze_user_spotify(sp: Spotify, user_id: str) -> Dict[str, Any]:
    """
    Análisis GLOBAL de las playlists y hábitos de escucha de un usuario de Spotify.
    
    Args:
        sp: instancia del cliente Spotify autenticada.
        user_id: el ID del usuario de Spotify.
        
    Returns:
        Diccionario que contiene:
        - username: nombre de usuario.
        - playlists: DataFrame con información de playlists.
        - all_tracks: DataFrame con todas las canciones de todas las playlists.
        - recommendations: DataFrame con canciones recomendadas.
    """
    df_playlists, username = get_user_public_playlists(sp, user_id)

    print(f"\nUsuario {username} tiene {len(df_playlists)} playlists públicas")

    all_tracks_df_list = []

    for _, row in df_playlists.iterrows():
        print(f"\nExtrayendo playlist: {row['playlist_name']}")
        all_tracks, _ = get_all_playlist_tracks(sp, row['playlist_id'])
        df_tracks = create_df(all_tracks)
        df_tracks['playlist_name'] = row['playlist_name']
        all_tracks_df_list.append(df_tracks)

    df_all_tracks = pd.concat(all_tracks_df_list, ignore_index=True)
    print(f"\nTotal de canciones analizadas: {len(df_all_tracks)}")

    print("\nAnalizando hábitos del usuario...")

    plt.figure()
    sns.countplot(x='added_weekday', data=df_all_tracks, order=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
    plt.title(f'Canciones agregadas por día de semana - {username}')
    plt.show()

    plt.figure()
    sns.countplot(x='added_hour', data=df_all_tracks)
    plt.title(f'Canciones agregadas por hora - {username}')
    plt.show()

    top_artists = df_all_tracks['artists'].value_counts().head(10)
    plt.figure()
    sns.barplot(y=top_artists.index, x=top_artists.values)
    plt.title(f'Top 10 artistas - {username}')
    plt.xlabel('Cantidad de canciones')
    plt.show()

    print("\nGenerando recomendaciones...")

    top_tracks = df_all_tracks.sort_values(by='popularity', ascending=False)['track_id'].head(5).tolist()

    top_artists_list = df_all_tracks['artists'].value_counts().head(3).index.tolist()
    
    artist_seeds = []
    for artist_name in top_artists_list:
        res = sp.search(q=f'artist:{artist_name}', type='artist', limit=1)
        if res['artists']['items']:
            artist_seeds.append(res['artists']['items'][0]['id'])

    df_recs = recommend_from_artists(sp, df_all_tracks)
    print(f"Se generaron exitosamente {len(df_recs)} recomendaciones para {username}")

    return {
        'username': username,
        'playlists': df_playlists,
        'all_tracks': df_all_tracks,
        'recommendations': df_recs
    }


#region GRAFICO DE RADAR

def playlist_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extraer y calcular características agregadas para cada playlist.
    
    Calcula duración, popularidad y métricas proxy personalizadas (alegría, energía)
    para cada playlist en el dataset.
    
    Args:
        df: DataFrame con información de canciones agrupado por playlist.
        
    Returns:
        DataFrame con una fila por playlist que contiene características calculadas.
    """
    grouped = df.groupby("playlist_name")

    features = grouped.apply(lambda x: pd.Series({
        "duracion_total_min": x["duration_minutes"].sum(),
        "duracion_media_tema": x["duration_minutes"].mean(),
        "popularidad_media": x["popularity"].mean(),
        "ratio_explicito": x["explicit"].mean(),

        # !!!! METRICAS PROXY A REVISAR → pueden estar muy mal y ser engañosas
        # TODO: hace falta investigar mejores formas de medir alegría y energía... 
        "alegria_proxy": (
            x["popularity"].mean() * (1 - x["explicit"].mean())
        ),
        "energia_proxy": (
            (1 / x["duration_minutes"].mean()) * (1 + x["explicit"].mean())
        )
    }))

    return features.reset_index()


def radar_playlists(df: pd.DataFrame, feature_cols: List[str]) -> None:
    """
    Crear un gráfico de radar comparando playlists en múltiples características.
    
    Visualiza características normalizadas para cada playlist en un gráfico de radar
    multi-eje para fácil comparación.
    
    Args:
        df: DataFrame con características normalizadas de playlists.
        feature_cols: Lista de nombres de columnas de características a mostrar en el radar.
        
    Returns:
        None. Muestra el gráfico.
    """
    labels = feature_cols
    num_vars = len(labels)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True))

    for _, row in df.iterrows():
        values = row[feature_cols].tolist()
        values += values[:1]

        ax.plot(angles, values, linewidth=2, label=row["playlist_name"])
        ax.fill(angles, values, alpha=0.1)

    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.tick_params(axis="x", pad=18)
    ax.set_title("Comparación de Playlists", pad=10)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=2,
        frameon=False
    )

    plt.show()


def normalize_features(df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    """
    Normalizar características especificadas en un DataFrame con MinMaxScaler.
    
    Escala las columnas de características al rango [0, 1] manteniendo la estructura
    del DataFrame original.
    
    Args:
        df: DataFrame de entrada que contiene las características a normalizar.
        feature_cols: lista de nombres de columnas a normalizar.
        
    Returns:
        DataFrame con características normalizadas.
    """
    scaler = MinMaxScaler()
    df_scaled = df.copy()
    df_scaled[feature_cols] = scaler.fit_transform(df[feature_cols])
    return df_scaled

#endregion