#!/usr/bin/env python3
import json, os, requests
from pathlib import Path
from datetime import date, timedelta

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(exist_ok=True)
TOKEN=os.getenv('TMDB_READ_TOKEN','').strip()
HEAD={'Authorization':f'Bearer {TOKEN}','accept':'application/json'} if TOKEN else {}

OFFICIAL=[
 {"id":"premium-max","name":"Max / HBO","type":"service","group":"💎 PREMIUM LIVE CHANNELS","provider":"Max / HBO","language":"en/es","url":"https://www.max.com/","overview":"Official Max/HBO access. Subscription and DRM apply; opens the official service."},
 {"id":"premium-cinemax","name":"Cinemax","type":"service","group":"💎 PREMIUM LIVE CHANNELS","provider":"Cinemax","language":"en","url":"https://www.cinemax.com/order","overview":"Official Cinemax subscription/provider access. Not an open M3U feed."},
 {"id":"premium-starz","name":"STARZ / STARZ ENCORE","type":"service","group":"💎 PREMIUM LIVE CHANNELS","provider":"STARZ","language":"en/es","url":"https://www.starz.com/us/en/","overview":"Official STARZ service; STARZ ENCORE brands are available where included by your plan/provider."},
 {"id":"premium-paramount","name":"Paramount+ / SHOWTIME","type":"service","group":"💎 PREMIUM LIVE CHANNELS","provider":"Paramount+","language":"en/es","url":"https://www.paramountplus.com/","overview":"Official Paramount+ / SHOWTIME access. Plan availability varies."},

 {"id":"sports-nba-lp","name":"NBA League Pass","type":"service","group":"🏀 NBA LEAGUE PASS","provider":"NBA","language":"en/es","url":"https://www.nba.com/watch/league-pass-stream","overview":"Official NBA live and on-demand service. U.S./Canada blackout restrictions apply."},
 {"id":"sports-mlbtv","name":"MLB.TV","type":"service","group":"⚾ MLB.TV","provider":"MLB","language":"en/es","url":"https://www.mlb.com/live-stream-games","overview":"Official MLB live-game service. Blackout and exclusivity restrictions can apply."},
 {"id":"sports-nflplus","name":"NFL+","type":"service","group":"🏈 NFL+","provider":"NFL","language":"en","url":"https://www.nfl.com/plus","overview":"Official NFL service: local/primetime mobile games, NFL Network and more depending on plan/device."},
 {"id":"sports-f1tv","name":"F1 TV","type":"service","group":"🏎 F1 TV","provider":"Formula 1","language":"multi","url":"https://www.formula1.com/en-us/subscribe-to-f1-tv","overview":"Official F1 live sessions, onboard cameras, team radio, replays and archive depending on plan/region."},
 {"id":"sports-espn","name":"ESPN","type":"service","group":"📡 ESPN","provider":"ESPN","language":"en/es","url":"https://plus.espn.com/","overview":"Official ESPN streaming access; includes ESPN networks/ESPN+ content depending on plan."},

 {"id":"fast-tubi-sports","name":"Tubi — Live Sports","type":"service","group":"🟢 FREE SPORTS FAST","provider":"Tubi","language":"en/es","url":"https://tubitv.com/category/sports_on_tubi","overview":"Free legal sports hub. Tubi lists NFL Channel, MLB, NHL, The NBA Channel, UFC, NASCAR, PGA TOUR, beIN Sports XTRA and more; lineup varies."},
 {"id":"fast-pluto-live","name":"Pluto TV — Live TV","type":"service","group":"🟢 FREE SPORTS FAST","provider":"Pluto TV","language":"en/es","url":"https://pluto.tv/us/live-tv/","overview":"Free legal live TV with sports, news, movies, shows and kids channels."},
 {"id":"fast-sling-es","name":"Sling Freestream — Español","type":"service","group":"🟢 FREE SPORTS FAST","provider":"Sling Freestream","language":"es","url":"https://www.sling.com/latino-es/freestream","overview":"Free legal Spanish live TV and on-demand; Sling advertises 70+ Spanish channels plus access to hundreds of English channels."},
 {"id":"fast-plex","name":"Plex — Free Live TV","type":"service","group":"🟢 FREE SPORTS FAST","provider":"Plex","language":"multi","url":"https://www.plex.tv/watch-free-tv/","overview":"Free ad-supported live TV and on-demand across many supported devices."},
 {"id":"fast-tubi-movies","name":"Tubi — Movies","type":"service","group":"🎬 FREE MOVIES FAST","provider":"Tubi","language":"en/es","url":"https://tubitv.com/category/movies","overview":"Free legal movies with ads."},
 {"id":"fast-pluto-movies","name":"Pluto TV — Movies","type":"service","group":"🎬 FREE MOVIES FAST","provider":"Pluto TV","language":"en/es","url":"https://pluto.tv/us/on-demand/movies/","overview":"Free legal movies and movie channels with ads."},
 {"id":"fast-tubi-series","name":"Tubi — Series","type":"service","group":"📺 FREE SERIES FAST","provider":"Tubi","language":"en/es","url":"https://tubitv.com/category/tv","overview":"Free legal TV series and shows with ads."},
 {"id":"fast-pluto-series","name":"Pluto TV — Shows","type":"service","group":"📺 FREE SERIES FAST","provider":"Pluto TV","language":"en/es","url":"https://pluto.tv/us/on-demand/series/","overview":"Free legal TV series and themed live channels."},

 {"id":"free-tubi-movies","name":"Tubi — Movies & TV","type":"service","group":"🎬 ON DEMAND MOVIES","provider":"Tubi","language":"en/es","url":"https://tubitv.com/","overview":"Free legal movies and TV with ads."},
 {"id":"free-tubi-series","name":"Tubi — Series","type":"service","group":"📺 ON DEMAND SERIES","provider":"Tubi","language":"en/es","url":"https://tubitv.com/","overview":"Free legal series and TV with ads."},
 {"id":"free-pluto","name":"Pluto TV — On Demand","type":"service","group":"🎬 ON DEMAND MOVIES","provider":"Pluto TV","language":"en/es","url":"https://pluto.tv/us/on-demand/","overview":"Free legal on-demand movies and series with ads."}
]
def get(path,params=None):
    r=requests.get('https://api.themoviedb.org/3'+path,headers=HEAD,params=params or {},timeout=25)
    r.raise_for_status(); return r.json()

def poster(path):
    return 'https://image.tmdb.org/t/p/w500'+path if path else ''

def provider_url(kind, ident):
    # TMDB watch-provider endpoint returns the canonical TMDB watch page; provider-specific deep links are not guaranteed.
    try:
        d=get(f'/{kind}/{ident}/watch/providers')
        us=(d.get('results') or {}).get('US') or {}
        return us.get('link') or f'https://www.themoviedb.org/{kind}/{ident}/watch'
    except Exception:
        return f'https://www.themoviedb.org/{kind}/{ident}'

def pack_movie(m, group, lang):
    return {"id":f"movie-{m['id']}-{group}","tmdb_id":m['id'],"name":m.get('title') or m.get('original_title') or 'Movie',"type":"vod","media_type":"movie","group":group,"provider":"TMDB / JustWatch availability","language":lang,"poster":poster(m.get('poster_path')),"backdrop":poster(m.get('backdrop_path')),"overview":m.get('overview') or '',"year":(m.get('release_date') or '')[:4],"rating":m.get('vote_average'),"url":provider_url('movie',m['id'])}

def pack_tv(m, group, lang):
    return {"id":f"tv-{m['id']}-{group}","tmdb_id":m['id'],"name":m.get('name') or m.get('original_name') or 'Series',"type":"vod","media_type":"tv","group":group,"provider":"TMDB / JustWatch availability","language":lang,"poster":poster(m.get('poster_path')),"backdrop":poster(m.get('backdrop_path')),"overview":m.get('overview') or '',"year":(m.get('first_air_date') or '')[:4],"rating":m.get('vote_average'),"url":provider_url('tv',m['id'])}

items=list(OFFICIAL)
status={'tmdb_enabled':bool(TOKEN),'items':len(items)}
if TOKEN:
    today=date.today(); start=(today-timedelta(days=180)).isoformat(); end=(today+timedelta(days=45)).isoformat()
    seen=set()
    # English new releases
    for page in range(1,4):
        data=get('/discover/movie',{'language':'en-US','region':'US','sort_by':'primary_release_date.desc','primary_release_date.gte':start,'primary_release_date.lte':end,'include_adult':'false','page':page})
        for m in data.get('results',[]):
            key=('movie',m['id'],'en')
            if key not in seen: items.append(pack_movie(m,'🆕 NEW RELEASES EN','en-US')); seen.add(key)
    # Spanish-localized new releases
    for page in range(1,4):
        data=get('/discover/movie',{'language':'es-US','region':'US','sort_by':'primary_release_date.desc','primary_release_date.gte':start,'primary_release_date.lte':end,'include_adult':'false','page':page})
        for m in data.get('results',[]):
            key=('movie',m['id'],'es')
            if key not in seen: items.append(pack_movie(m,'🆕 ESTRENOS ESPAÑOL','es-US')); seen.add(key)
    # On-demand movies, popular
    for page in range(1,3):
        data=get('/movie/popular',{'language':'en-US','region':'US','page':page})
        for m in data.get('results',[]):
            items.append(pack_movie(m,'🎬 ON DEMAND MOVIES','en-US'))
    # On-demand series, popular
    for page in range(1,3):
        data=get('/tv/popular',{'language':'en-US','page':page})
        for m in data.get('results',[]):
            items.append(pack_tv(m,'📺 ON DEMAND SERIES','en-US'))
    status={'tmdb_enabled':True,'items':len(items)}
(OUT/'vod.json').write_text(json.dumps(items,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(OUT/'vod_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(status))
