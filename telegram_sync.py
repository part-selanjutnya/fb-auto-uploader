import os
import json
import requests
import subprocess

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN tidak ditemukan.")
    exit(1)

videos_file = 'videos.json'
existing_videos = []
if os.path.exists(videos_file):
    try:
        with open(videos_file, 'r') as f:
            existing_videos = json.load(f)
    except:
        existing_videos = []

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)
if response.status_code != 200:
    print("Gagal mengambil pembaruan dari Telegram.")
    exit(1)

data = response.json()
messages = data.get('result', [])

new_videos_added = 0
max_id = max([v.get('id', 0) for v in existing_videos], default=0)

for msg in messages:
    video_obj = None
    caption = ""
    
    if 'message' in msg:
        m = msg['message']
        if 'video' in m:
            video_obj = m['video']
            caption = m.get('caption', 'Video Alur Cerita Afiliasi')
    elif 'channel_post' in msg:
        m = msg['channel_post']
        if 'video' in m:
            video_obj = m['video']
            caption = m.get('caption', 'Video Alur Cerita Afiliasi')

    if video_obj:
        file_id = video_obj.get('file_id')
        
        # Cek apakah file_id sudah ada di database
        already_exists = any(v.get('file_id') == file_id for v in existing_videos)
        if already_exists:
            continue

        # Ambil jalur file dari Telegram API
        file_path_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_res = requests.get(file_path_url).json()
        
        if file_res.get('ok'):
            file_path = file_res['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            
            max_id += 1
            new_id = max_id
            
            # Unduh sampel video sebentar untuk ekstrak thumbnail via FFmpeg
            temp_vid = "temp_thumb.mp4"
            temp_img = f"thumb_{new_id}.jpg"
            thumbnail_url = ""
            
            try:
                vid_data = requests.get(download_url, stream=True)
                with open(temp_vid, 'wb') as tv:
                    for chunk in vid_data.iter_content(chunk_size=8192):
                        tv.write(chunk)
                
                # Ekstrak frame pertama menggunakan FFmpeg
                subprocess.run(['ffmpeg', '-i', temp_vid, '-ss', '00:00:01', '-vframes', '1', temp_img, '-y'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if os.path.exists(temp_img) and os.path.getsize(temp_img) > 0:
                    # Karena GitHub Pages adalah web statis, kita bisa simpan path lokal atau base64 data URI kecil
                    # Atau sederhananya kita konversi ke base64 agar langsung tampil di JSON tanpa perlu hosting gambar terpisah
                    import base64
                    with open(temp_img, 'rb') as img_file:
                        b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                        thumbnail_url = f"data:image/jpeg;base64,{b64_data}"
                
                for tmp in [temp_vid, temp_img]:
                    if os.path.exists(tmp):
                        os.remove(tmp)
            except Exception as e:
                print(f"Gagal membuat thumbnail: {e}")

            new_video_entry = {
                "id": new_id,
                "file_id": file_id,
                "title": caption.split('\n')[0] if caption else "Video Alur Cerita",
                "url": download_url,
                "thumbnail": thumbnail_url,
                "description": caption,
                "comment_text": "👇 Lanjutannya dan barang di video ada di link ini:",
                "redirect_link": "",
                "status": "pending",
                "scheduled_time": None,
                "target_pages": ["Semua"]
            }
            
            existing_videos.append(new_video_entry)
            new_videos_added += 1

if new_videos_added > 0:
    try:
        with open(videos_file, 'w') as f:
            json.dump(existing_videos, f, indent=4)
        print(f"Berhasil menambahkan {new_videos_added} video baru ke antrean.")
    except Exception as e:
        print(f"Gagal menyimpan file videos.json: {e}")
else:
    print("Tidak ada video baru yang ditemukan.")
