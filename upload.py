import os
import json
import requests
import datetime
import gdown

# Mendapatkan jam saat ini dalam waktu Indonesia (WIB / UTC+7)
current_hour = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).hour
print(f"Jam sistem saat ini (WIB): {current_hour}:00")

# Memuat data Fanpage dari file pages.json
pages_file = 'pages.json'
all_pages = []

if os.path.exists(pages_file):
    try:
        with open(pages_file, 'r') as f:
            all_pages = json.load(f)
    except Exception as e:
        print(f"Error memuat pages.json: {e}")
else:
    print("File pages.json tidak ditemukan!")

videos_file = 'videos.json'
if not os.path.exists(videos_file):
    print("File videos.json tidak ditemukan!")
    exit(0)

try:
    with open(videos_file, 'r') as f:
        videos = json.load(f)
except Exception as e:
    print(f"Error membaca videos.json: {e}")
    exit(0)

# Cek apakah ini dipicu via Instant Upload (Manual dari Web)
target_pages_input = []
is_instant_upload = False
event_path = os.environ.get('GITHUB_EVENT_PATH')
if event_path and os.path.exists(event_path):
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            target_pages_input = event_data.get('client_payload', {}).get('target_pages', [])
            if target_pages_input:
                is_instant_upload = True
    except Exception as e:
        print(f"Error membaca event payload: {e}")

# Cari video pertama yang berstatus 'pending'
target_video = None
target_index = -1

for index, video in enumerate(videos):
    if video.get('status') == 'pending':
        if not is_instant_upload:
            schedule_hours = video.get('schedule_hours', [])
            if schedule_hours and current_hour not in schedule_hours:
                print(f"Video ID {video.get('id')} dilewati (Dijadwalkan jam {schedule_hours}, sekarang jam {current_hour}).")
                continue
        
        target_video = video
        target_index = index
        break

if not target_video:
    print("Tidak ada video pending yang cocok dengan jadwal jam saat ini.")
    exit(0)

video_id_db = target_video.get('id')
video_url = target_video.get('url')
video_title = target_video.get('title', 'Video Reels')
video_desc = target_video.get('description', '')
video_targets = target_video.get('target_pages', ["Semua"])

print(f"Memproses video ID: {video_id_db} - {video_title}")

# Menentukan Fanpage tujuan
if is_instant_upload:
    pages_data = [p for p in all_pages if p.get('name') in target_pages_input]
    print(f"Mode Upload Instan - Target Fanpage: {target_pages_input}")
elif video_targets and "Semua" not in video_targets:
    pages_data = [p for p in all_pages if p.get('name') in video_targets]
    print(f"Mode Jadwal Cron - Target Spesifik: {video_targets}")
else:
    pages_data = all_pages
    print("Mode Otomatis - Semua Fanpage diproses.")

# Mengunduh video dari Google Drive
output_filename = 'temp_video.mp4'
if os.path.exists(output_filename):
    os.remove(output_filename)

try:
    print("Mengunduh file video dari Google Drive...")
    gdown.download(video_url, output_filename, quiet=False)
except Exception as e:
    print(f"Gagal mengunduh video: {e}")
    exit(1)

if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
    print("Gagal: File video kosong atau tidak berhasil diunduh.")
    exit(1)

file_size = os.path.getsize(output_filename)
success_upload_count = 0

# Mengunggah video menggunakan metode 3 tahap ke Fanpage tujuan
for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        continue
        
    print(f"Mengunggah Reels ke halaman: {page_name} ({page_id})...")
    video_graph_url = f"https://graph-video.facebook.com/v26.0/{page_id}/videos"
    
    try:
        # TAHAP 1: START
        start_res = requests.post(video_graph_url, data={
            'access_token': page_token,
            'upload_phase': 'start',
            'file_size': file_size
        }).json()
        
        if 'upload_session_id' not in start_res:
            print(f"-> Gagal di Tahap Start untuk {page_name}: {start_res}")
            continue
            
        upload_session_id = start_res['upload_session_id']
        start_offset = int(start_res.get('start_offset', 0))
        end_offset = int(start_res.get('end_offset', file_size))
        
        # TAHAP 2: TRANSFER
        with open(output_filename, 'rb') as video_file:
            video_file.seek(start_offset)
            chunk_data = video_file.read(end_offset - start_offset)
            
        transfer_res = requests.post(video_graph_url, data={
            'access_token': page_token,
            'upload_phase': 'transfer',
            'upload_session_id': upload_session_id,
            'start_offset': start_offset
        }, files={'video_file_chunk': ('chunk.mp4', chunk_data, 'video/mp4')}).json()
        
        # TAHAP 3: FINISH
        finish_res = requests.post(video_graph_url, data={
            'access_token': page_token,
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'description': f"{video_title}\n\n{video_desc}",
            'publishing_phase': 'post'
        }).json()
        
        if finish_res.get('success') or finish_res.get('id'):
            print(f"-> Sukses terunggah sebagai Reels ke {page_name}!")
            success_upload_count += 1
        else:
            print(f"-> Gagal di Tahap Finish untuk {page_name}: {finish_res}")
            
    except Exception as e:
        print(f"-> Terjadi error saat mengunggah ke {page_name}: {e}")

# Ubah status di videos.json jika berhasil
if success_upload_count > 0:
    videos[target_index]['status'] = 'completed'
    try:
        with open(videos_file, 'w') as f:
            json.dump(videos, f, indent=4)
        print("videos.json berhasil diperbarui.")
    except Exception as e:
        print(f"Gagal memperbarui videos.json: {e}")

if os.path.exists(output_filename):
    os.remove(output_filename)

print("Proses upload selesai.")
