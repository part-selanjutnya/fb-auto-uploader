import os
import json
import requests

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
VIDEOS_FILE = 'videos.json'

def get_latest_telegram_video():
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram Bot Token belum diatur.")
        return None
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if not res.get('ok'):
            print(f"Gagal mengambil update dari Telegram: {res}")
            return None
            
        updates = res.get('result', [])
        for update in reversed(updates):
            message = update.get('message', {})
            video = message.get('video') or message.get('document')
            if video:
                file_id = video.get('file_id')
                file_name = video.get('file_name', 'Video Telegram')
                caption = message.get('caption', 'Alur Cerita Part')
                
                file_path_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                file_res = requests.get(file_path_url).json()
                if file_res.get('ok'):
                    file_path = file_res['result']['file_path']
                    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                    return {
                        "url": download_url,
                        "title": file_name.rsplit('.', 1)[0],
                        "caption": caption
                    }
    except Exception as e:
        print(f"Error saat membaca Telegram API: {e}")
    return None

def main():
    new_video = get_latest_telegram_video()
    if not new_video:
        print("Tidak ada video baru di Telegram.")
        return
        
    print(f"Menemukan video baru dari Telegram: {new_video['title']}")
    
    if os.path.exists(VIDEOS_FILE):
        try:
            with open(VIDEOS_FILE, 'r') as f:
                videos = json.load(f)
        except:
            videos = []
    else:
        videos = []
        
    max_id = max([v.get('id', 0) for v in videos], default=0)
    new_id = max_id + 1
    
    default_desc = "https://part-selanjutnya.github.io/Klik-disini/\nTonton selanjutnya☝️\n#AlurCeritaFilm #ShortMovie #FilmPendek #CeritaSeru #DramaReels #CuplikanFilm #SinopsisFilm #RekomendasiFilm #FacebookReels #ReelsViral #FYPReels #ReelsIndonesia #VideoViral #TrendingReels"
    final_desc = new_video['caption'] if new_video['caption'] != 'Alur Cerita Part' else default_desc

    video_entry = {
        "id": new_id,
        "url": new_video['url'],
        "title": f"Part {new_id} - {new_video['title']}",
        "description": final_desc,
        "target_pages": ["Semua"],
        "schedule_hours": [12, 17, 20],
        "status": "pending"
    }
    
    videos.append(video_entry)
    
    with open(VIDEOS_FILE, 'w') as f:
        json.dump(videos, f, indent=4)
        
    print(f"Video Part {new_id} berhasil dimasukkan ke videos.json dari Telegram!")

if __name__ == '__main__':
    main()
