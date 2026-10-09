import os
import json
import requests
import gdown

# Memuat data Fanpage dari Environment GitHub Secrets
pages_data_env = os.environ.get('FB_PAGES_DATA', '[]')
try:
    pages_data = json.loads(pages_data_env)
except Exception as e:
    print(f"Error memuat FB_PAGES_DATA: {e}")
    pages_data = []

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
print(f"URL: {video_url}")

# Mengunduh video dari Google Drive ke penyimpanan lokal workflow
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

print("Unduhan berhasil.")

file_size = os.path.getsize(output_filename)
success_upload_count = 0

# Mengunggah video menggunakan metode 3 tahap (Start -> Transfer -> Finish) ke setiap Fanpage
for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        continue
        
    print(f"Mengunggah Reels ke halaman: {page_name} ({page_id})...")
    video_graph_url = f"https://graph-video.facebook.com/v26.0/{page_id}/videos"
    
    try:
        # --- TAHAP 1: START ---
        start_payload = {
            'access_token': page_token,
            'upload_phase': 'start',
            'file_size': file_size
        }
        start_res = requests.post(video_graph_url, data=start_payload).json()
        
        if 'upload_session_id' not in start_res:
            print(f"-> Gagal di Tahap Start untuk {page_name}: {start_res}")
            continue
            
        upload_session_id = start_res['upload_session_id']
        start_offset = int(start_res.get('start_offset', 0))
        end_offset = int(start_res.get('end_offset', file_size))
        
        # --- TAHAP 2: TRANSFER ---
        with open(output_filename, 'rb') as video_file:
            video_file.seek(start_offset)
            chunk_data = video_file.read(end_offset - start_offset)
            
        transfer_payload = {
            'access_token': page_token,
            'upload_phase': 'transfer',
            'upload_session_id': upload_session_id,
            'start_offset': start_offset
        }
        files = {'video_file_chunk': ('chunk.mp4', chunk_data, 'video/mp4')}
        
        transfer_res = requests.post(video_graph_url, data=transfer_payload, files=files).json()
        
        # --- TAHAP 3: FINISH ---
        finish_payload = {
            'access_token': page_token,
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'description': f"{video_title}\n\n{video_desc}",
            'publishing_phase': 'post'
        }
        finish_res = requests.post(video_graph_url, data=finish_payload).json()
        
        if finish_res.get('success') or finish_res.get('id'):
            print(f"-> Sukses terunggah sebagai Reels ke {page_name}!")
            success_upload_count += 1
        else:
            print(f"-> Gagal di Tahap Finish untuk {page_name}: {finish_res}")
            
    except Exception as e:
        print(f"-> Terjadi error saat mengunggah ke {page_name}: {e}")

# Jika berhasil diunggah ke setidaknya satu halaman, ubah status di videos.json menjadi 'completed'
if success_upload_count > 0:
    videos[target_index]['status'] = 'completed'
    try:
        with open(videos_file, 'w') as f:
            json.dump(videos, f, indent=4)
        print("videos.json berhasil diperbarui menjadi 'completed'.")
    except Exception as e:
        print(f"Gagal memperbarui videos.json: {e}")
else:
    print("Peringatan: Video gagal diunggah ke semua halaman, status tetap 'pending'.")

# Membersihkan file video sementara
if os.path.exists(output_filename):
    os.remove(output_filename)

print("Proses upload selesai.")
