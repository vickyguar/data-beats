# TODO 
# - Agregar type hints y docstrings
# - Agregar regions
# pensar en nuevos analsis
# sacar info



import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from tqdm import tqdm


def normalize_features(df, feature_cols):
    scaler = MinMaxScaler()
    df_scaled = df.copy()
    df_scaled[feature_cols] = scaler.fit_transform(df[feature_cols])
    return df_scaled


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

    print("🎉 DataFrame final creado")
    
    return df


def get_user_public_playlists(sp, user_id):
    user_info = sp.user(user_id)
    username = user_info.get('display_name', user_id)

    print(f"👤 Usuario: {username}")
    print("⏳ Extrayendo playlists públicas...\n")

    playlists = []
    offset = 0
    limit = 50

    # Primera llamada para saber el total
    first_response = sp.user_playlists(user_id, limit=limit, offset=offset)
    total_playlists = first_response['total']
    playlists.extend(first_response['items'])

    with tqdm(total=total_playlists, desc="📀 Playlists") as pbar:
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

    print(f"✅ {len(df_playlists)} playlists públicas extraídas exitosamente")

    return df_playlists, username




def recommend_from_artists(sp, df_user_tracks, limit_per_artist=2, max_artists=5):
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



def analyze_user_spotify(sp, user_id):
    
    df_playlists, username = get_user_public_playlists(sp, user_id)

    print(f"\n📊 Usuario {username} tiene {len(df_playlists)} playlists públicas")

    all_tracks_df_list = []

    for idx, row in df_playlists.iterrows():
        print(f"\n🔹 Extrayendo playlist: {row['playlist_name']}")
        all_tracks, _ = get_all_playlist_tracks(sp, row['playlist_id'])
        df_tracks = create_df(all_tracks)
        df_tracks['playlist_name'] = row['playlist_name']
        all_tracks_df_list.append(df_tracks)

    df_all_tracks = pd.concat(all_tracks_df_list, ignore_index=True)
    print(f"\n🎉 Total canciones analizadas: {len(df_all_tracks)}")

    print("\n📈 Análisis de hábitos del usuario")

    plt.figure()
    sns.countplot(x='added_weekday', data=df_all_tracks, order=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
    plt.title(f'Canciones agregadas por día de la semana - {username}')
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

    print("\n🎯 Generando recomendaciones...")

    top_tracks = df_all_tracks.sort_values(by='popularity', ascending=False)['track_id'].head(5).tolist()

    top_artists_list = df_all_tracks['artists'].value_counts().head(3).index.tolist()
    
    artist_seeds = []
    for artist_name in top_artists_list:
        res = sp.search(q=f'artist:{artist_name}', type='artist', limit=1)
        if res['artists']['items']:
            artist_seeds.append(res['artists']['items'][0]['id'])

    df_recs = recommend_from_artists(sp, df_all_tracks)
    print(f"✅ Se generaron {len(df_recs)} recomendaciones para {username}")

    return {
        'username': username,
        'playlists': df_playlists,
        'all_tracks': df_all_tracks,
        'recommendations': df_recs
    }
  
  
def playlist_features(df):
    grouped = df.groupby("playlist_name")

    features = grouped.apply(lambda x: pd.Series({
        "duracion_total_min": x["duration_minutes"].sum(),
        "duracion_media_tema": x["duration_minutes"].mean(),
        "popularidad_media": x["popularity"].mean(),
        "ratio_explicito": x["explicit"].mean(),

        # proxies
        "alegria_proxy": (
            x["popularity"].mean() * (1 - x["explicit"].mean())
        ),
        "energia_proxy": (
            (1 / x["duration_minutes"].mean()) * (1 + x["explicit"].mean())
        )
    }))

    return features.reset_index()


def radar_playlists(df, feature_cols):
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
