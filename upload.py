import os
import json
import requests
import gdown

# Memuat data Fanpage dari Environment GitHub Secrets
pages_data_env = os.environ.get('FB_PAGES_DATA', '[]')
try:
    all_pages = json.loads(pages_data_env)
except Exception as e:
    print(f"Error memuat FB_PAGES_DATA: {e}")
    all_pages = []

# Mendapatkan target halaman yang dipilih dari payload event (jika dipicu via instant upload)
target_pages_input = []
event_path = os.environ.get('GITHUB_EVENT_PATH')
if event_path and os.path.exists(event_path):
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            # Mengambil dari client_payload jika ada
            target_pages_input = event_data.get('client_payload', {}).get('target_pages', [])
    except Exception as e:
        print(f"Error membaca event payload: {e}")

# Jika berjalan via cron/manual biasa tanpa pilihan spesifik, gunakan semua halaman. 
# Jika dari instant upload, filter hanya halaman yang dicentang.
if target_pages_input:
    pages_data = [p for p in all_pages if p.get('name') in target_pages_input]
    print(f"Mode Upload Instan - Target Fanpage: {target_pages_input}")
else:
    pages_data = all_pages
    print("Mode Otomatis / Manual Workflow - Semua Fanpage diproses.")

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

# Cari video pertama yang berstatus 'pending'
target_video = None
target_index = -1

for index, video in enumerate(videos):
    if video.get('status') == 'pending':
        target_video = video
        target_index = index
        break

if not target_video:
    print("Tidak ada video dengan status 'pending' di dalam antrean.")
    exit(0)

video_id_db = target_video.get('id')
video_url = target_video.get('url')
video_title = target_video.get('title', 'Video Reels')
video_desc = target_video.get('description', '')

print(f"Memproses video ID: {video_id_db} - {video_title}")

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

# Mengunggah video menggunakan metode 3 tahap ke Fanpage yang difilter
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

# Ubah status di videos.json jika berhasil diunggah ke target yang dipilih
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
