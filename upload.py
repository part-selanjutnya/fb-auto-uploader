import os
import json
import requests
import datetime
import time
import random
import subprocess
import gdown

current_hour = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).hour
print(f"Jam sistem saat ini (WIB): {current_hour}:00")

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

target_pages_input = []
is_instant_upload = False
event_path = os.environ.get('GITHUB_EVENT_PATH')
if event_path and os.path.exists(event_path):
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            payload = event_data.get('client_payload', {})
            
            # --- 1. REM DARURAT ---
            # Jika perintah dari web adalah sync_only, batalkan proses upload!
            if payload.get('command') == 'sync_only':
                print("Mode Tarik Data Aktif: Skrip upload dihentikan agar video masuk antrean (Pending).")
                exit(0)
            
            target_pages_input = payload.get('target_pages', [])
            if target_pages_input:
                is_instant_upload = True
    except Exception as e:
        print(f"Error membaca event payload: {e}")

target_video = None
target_index = -1

for index, video in enumerate(videos):
    if video.get('status') == 'pending':
        if not is_instant_upload:
            schedule_hours = video.get('schedule_hours', [])
            if schedule_hours and current_hour not in schedule_hours:
                print(f"Video ID {video.get('id')} dilewati (Jadwal jam {schedule_hours}, sekarang jam {current_hour}).")
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
video_comment = target_video.get('comment_text', '') # Ambil komentar dari Web
video_link = target_video.get('redirect_link', '')   # Ambil link afiliasi dari Web
video_targets = target_video.get('target_pages', ["Semua"])

print(f"Memproses video ID: {video_id_db} - {video_title}")

if is_instant_upload:
    pages_data = [p for p in all_pages if p.get('name') in target_pages_input]
    print(f"Mode Upload Instan - Target Fanpage: {target_pages_input}")
elif video_targets and "Semua" not in video_targets:
    pages_data = [p for p in all_pages if p.get('name') in video_targets]
    print(f"Mode Jadwal Cron - Target Spesifik: {video_targets}")
else:
    pages_data = all_pages
    print("Mode Otomatis - Semua Fanpage diproses.")

raw_filename = 'raw_video.mp4'
output_filename = 'final_video.mp4'

for f_name in [raw_filename, output_filename]:
    if os.path.exists(f_name):
        os.remove(f_name)

try:
    print("Mengunduh file video...")
    gdown.download(video_url, raw_filename, quiet=False)
except Exception as e:
    print(f"Gagal mengunduh video: {e}")
    exit(1)

if not os.path.exists(raw_filename) or os.path.getsize(raw_filename) == 0:
    print("Gagal: File video kosong atau tidak berhasil diunduh.")
    exit(1)

# --- MODUL KECERDASAN: Mutasi Digital Hash Video via FFmpeg ---
print("🤖 Menjalankan Mutasi Digital Video (Anti-Duplicate Hash)...")
try:
    mutation_cmd = [
        'ffmpeg', '-i', raw_filename,
        '-ss', '0.3', 
        '-c:v', 'libx264', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        output_filename, '-y'
    ]
    subprocess.run(mutation_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except Exception as e:
    print(f"Mutasi FFmpeg dilewati, menggunakan video mentah: {e}")
    output_filename = raw_filename

if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
    output_filename = raw_filename

file_size = os.path.getsize(output_filename)
success_upload_count = 0

random.shuffle(pages_data)

for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        print(f"-> Token atau ID kosong untuk halaman {page_name}")
        continue
        
    print(f"Mengunggah Reels otonom ke halaman: {page_name}...")
    video_graph_url = f"https://graph-video.facebook.com/v26.0/{page_id}/videos"
    
    try:
        start_res = requests.post(video_graph_url, data={
            'access_token': page_token,
            'upload_phase': 'start',
            'file_size': file_size,
            'media_type': 'REELS'
        }).json()
        
        if 'upload_session_id' not in start_res:
            print(f"-> ❌ Gagal di Tahap Start untuk {page_name}: {start_res}")
            continue
            
        upload_session_id = start_res['upload_session_id']
        start_offset = int(start_res.get('start_offset', 0))
        end_offset = int(start_res.get('end_offset', file_size))
        
        with open(output_filename, 'rb') as video_file:
            video_file.seek(start_offset)
            chunk_data = video_file.read(end_offset - start_offset)
            
        transfer_res = requests.post(video_graph_url, data={
            'access_token': page_token,
            'upload_phase': 'transfer',
            'upload_session_id': upload_session_id,
            'start_offset': start_offset
        }, files={'video_file_chunk': ('chunk.mp4', chunk_data, 'video/mp4')}).json()
        
        finish_res = requests.post(video_graph_url, data={
            'access_token': page_token,
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'description': f"{video_title}\n\n{video_desc}",
            'media_type': 'REELS',
            'video_state': 'PUBLISHED'
        }).json()
        
        new_video_id = finish_res.get('id') or finish_res.get('video_id')
        
        if finish_res.get('success') or new_video_id:
            print(f"-> ✅ Sukses terunggah & dipublikasikan sebagai Reels ke {page_name} (ID: {new_video_id})!")
            success_upload_count += 1
            
            # --- 3. POSTING KOMENTAR AFILIASI TERINTEGRASI WEB ---
            if new_video_id:
                final_comment = ""
                # Gabungkan teks komentar dan link dari Web
                if video_comment:
                    final_comment = video_comment
                    if video_link:
                        final_comment += f"\n{video_link}"
                else:
                    # Alternatif jika belum sempat diedit di web
                    first_line_link = video_desc.splitlines()[0] if video_desc else ""
                    if first_line_link.startswith('http'):
                        final_comment = f"👇 Lanjutannya dan barang yang dipakai di video ada di link ini ya:\n{first_line_link}"

                if final_comment:
                    comment_url = f"https://graph.facebook.com/v26.0/{new_video_id}/comments"
                    try:
                        requests.post(comment_url, data={
                            'access_token': page_token,
                            'message': final_comment
                        })
                        print(f"   -> 💬 Komentar link afiliasi berhasil disematkan!")
                    except Exception as e:
                        pass
        else:
            print(f"-> ❌ Gagal di Tahap Finish untuk {page_name}: {finish_res}")
            
    except Exception as e:
        print(f"-> ❌ Terjadi error exception saat mengunggah ke {page_name}: {e}")

    # --- 2. KECEPATAN TINGGI ---
    delay_time = random.randint(3, 7)
    print(f"⏳ Jeda organik pemulihan algoritma selama {delay_time} detik...")
    time.sleep(delay_time)

if success_upload_count > 0:
    videos[target_index]['status'] = 'completed'
    
    cleaned_videos = []
    completed_videos = [v for v in videos if v.get('status') == 'completed']
    pending_videos = [v for v in videos if v.get('status') == 'pending']
    
    if completed_videos:
        cleaned_videos.append(completed_videos[-1])
    cleaned_videos.extend(pending_videos)
    
    try:
        with open(videos_file, 'w') as f:
            json.dump(cleaned_videos, f, indent=4)
    except:
        pass

for f_name in [raw_filename, output_filename]:
    if os.path.exists(f_name):
        os.remove(f_name)

print("Proses otonom mutasi & upload selesai dengan cepat.")
