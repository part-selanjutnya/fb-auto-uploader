import os
import requests
import json

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN tidak ditemukan.")
    exit(1)

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
response = requests.get(url).json()

if not response.get('ok'):
    print("Gagal terhubung ke Telegram API")
    exit(1)

updates = response.get('result', [])
if not updates:
    print("Tidak ada pesan baru.")
    exit(0)

videos_file = 'videos.json'
existing_videos = []
if os.path.exists(videos_file):
    try:
        with open(videos_file, 'r') as f:
            existing_videos = json.load(f)
    except:
        pass

new_videos_added = 0

# Proses BANYAK video sekaligus dari Telegram
for update in updates:
    message = update.get('message', {})
    video_obj = message.get('video')
    
    if video_obj:
        file_id = video_obj.get('file_id')
        caption = message.get('caption', 'Video Alur Cerita Afiliasi')
        
        # 1. Ambil URL File Video Utama
        file_info_url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
        file_info_res = requests.get(file_info_url).json()
        
        if file_info_res.get('ok'):
            file_path = file_info_res['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            
            # 2. Ambil URL Thumbnail (Gambar Pratinjau)
            thumbnail_url = ""
            thumb_obj = video_obj.get('thumbnail') or video_obj.get('thumb')
            if thumb_obj:
                thumb_file_id = thumb_obj.get('file_id')
                thumb_info_url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={thumb_file_id}"
                thumb_info_res = requests.get(thumb_info_url).json()
                if thumb_info_res.get('ok'):
                    thumb_file_path = thumb_info_res['result']['file_path']
                    thumbnail_url = f"https://api.telegram.org/file/bot{TOKEN}/{thumb_file_path}"
            
            # Cek apakah video sudah ada di antrean
            exists = any(v.get('url') == download_url for v in existing_videos)
            if not exists:
                new_id = len(existing_videos) + 1
                lines = caption.splitlines()
                title = lines[0] if lines else f"Video Part {new_id}"
                
                new_entry = {
                    "id": new_id,
                    "title": title,
                    "description": caption,
                    "comment_text": "", 
                    "redirect_link": "",
                    "url": download_url,
                    "thumbnail": thumbnail_url, # Menyimpan URL gambar Thumbnail
                    "status": "pending",
                    "target_pages": ["Semua"]
                }
                
                existing_videos.append(new_entry)
                new_videos_added += 1
                print(f"-> Masuk antrean pending: {title}")

if new_videos_added > 0:
    with open(videos_file, 'w') as f:
        json.dump(existing_videos, f, indent=4)
    print(f"Sukses menambahkan {new_videos_added} video ke dalam antrean!")
else:
    print("Tidak ada video baru atau semua sudah ada di antrean.")
