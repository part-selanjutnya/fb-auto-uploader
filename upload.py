import os
import json
import requests
import datetime
import time
import random
import subprocess
import gdown
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_spintax(text):
    if not text:
        return text
    pattern = re.compile(r'\{([^^{}]*)\}')
    while True:
        match = pattern.search(text)
        if not match:
            break
        options = match.group(1).split('|')
        text = text[:match.start()] + random.choice(options) + text[match.end():]
    return text

event_name = os.environ.get('GITHUB_EVENT_NAME', '')
if event_name == 'push':
    print("Aktivitas Edit/Hapus dari Web terdeteksi. Skrip Upload DIBEKUKAN.")
    exit(0)

event_path = os.environ.get('GITHUB_EVENT_PATH')
is_sync_only = False
is_instant_upload = False
target_video_id_inst = None

if event_path and os.path.exists(event_path):
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            payload = event_data.get('client_payload', {})
            command = payload.get('command')
            if command == 'sync_only':
                is_sync_only = True
            elif command == 'upload_now':
                target_video_id_inst = payload.get('video_id')
                is_instant_upload = True
    except:
        pass

if is_sync_only:
    print("Mode Tarik Data Selesai. Skrip upload dilewati.")
    exit(0)

pages_file = 'pages.json'
all_pages = []
if os.path.exists(pages_file):
    try:
        with open(pages_file, 'r') as f:
            all_pages = json.load(f)
    except:
        pass

videos_file = 'videos.json'
if not os.path.exists(videos_file):
    exit(0)

try:
    with open(videos_file, 'r') as f:
        videos = json.load(f)
except:
    exit(0)

target_video = None
target_index = -1
for index, video in enumerate(videos):
    if video.get('status') == 'pending':
        if is_instant_upload and target_video_id_inst is not None:
            if video.get('id') == target_video_id_inst:
                target_video = video
                target_index = index
                break
        elif not is_instant_upload:
            scheduled_time_str = video.get('scheduled_time')
            if scheduled_time_str:
                try:
                    sch_dt = datetime.datetime.strptime(scheduled_time_str, "%Y-%m-%dT%H:%M")
                    now_wib = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
                    if now_wib < sch_dt:
                        continue
                except:
                    pass
            target_video = video
            target_index = index
            break

if not target_video:
    print("Tidak ada video pending untuk di-upload.")
    exit(0)

video_id_db = target_video.get('id')
video_url = target_video.get('url')
video_title = target_video.get('title', 'Video Reels')
video_desc_template = target_video.get('description', '')
video_comment_template = target_video.get('comment_text', '') 
video_link = target_video.get('redirect_link', '')   
video_targets = target_video.get('target_pages', [])

if video_targets and "Semua" not in video_targets:
    pages_data = [p for p in all_pages if p.get('name') in video_targets]
else:
    pages_data = all_pages

raw_filename = 'raw_video.mp4'
output_filename = 'final_video.mp4'

for f_name in [raw_filename, output_filename]:
    if os.path.exists(f_name):
        os.remove(f_name)

print("Mengunduh file video...")
gdown.download(video_url, raw_filename, quiet=False)

if not os.path.exists(raw_filename) or os.path.getsize(raw_filename) == 0:
    print("Gagal mengunduh video dari Telegram.")
    exit(1)

print("🤖 Menjalankan Mutasi Digital Video Tingkat Lanjut...")
try:
    mutation_cmd = [
        'ffmpeg', '-i', raw_filename, 
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,eq=brightness=0.01:contrast=1.02', 
        '-c:v', 'libx264', '-crf', '24', '-preset', 'medium', 
        '-c:a', 'aac', '-b:a', '128k', 
        output_filename, '-y'
    ]
    subprocess.run(mutation_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
except Exception as e:
    print(f"Mutasi FFmpeg gagal: {e}, menggunakan file mentah.")
    output_filename = raw_filename

file_size = os.path.getsize(output_filename)

def upload_to_single_page(page):
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name', 'Unknown')
    
    if not page_token or not page_id:
        print(f"Token atau ID untuk Fanpage {page_name} tidak valid.")
        return False

    spun_title = process_spintax(video_title)
    spun_desc = process_spintax(video_desc_template)
    spun_comment = process_spintax(video_comment_template)
    
    video_graph_url = f"https://graph-video.facebook.com/v26.0/{page_id}/videos"
    try:
        print(f"Memulai sesi upload ke Fanpage: {page_name} (ID: {page_id})")
        start_res = requests.post(video_graph_url, data={'access_token': page_token, 'upload_phase': 'start', 'file_size': file_size, 'media_type': 'REELS'}).json()
        
        if 'upload_session_id' not in start_res:
            print(f"GAGAL START UPLOAD [{page_name}]: {json.dumps(start_res)}")
            return False
            
        upload_session_id = start_res['upload_session_id']
        start_offset = int(start_res.get('start_offset', 0))
        end_offset = int(start_res.get('end_offset', file_size))
        
        print(f"Mentransfer chunk data video ke {page_name}...")
        with open(output_filename, 'rb') as video_file:
            video_file.seek(start_offset)
            chunk_data = video_file.read(end_offset - start_offset)
            
        transfer_res = requests.post(video_graph_url, data={
            'access_token': page_token, 
            'upload_phase': 'transfer', 
            'upload_session_id': upload_session_id, 
            'start_offset': start_offset
        }, files={'video_file_chunk': ('chunk.mp4', chunk_data, 'video/mp4')}).json()
        
        print(f"Menyelesaikan sesi upload (finish) untuk {page_name}...")
        finish_res = requests.post(video_graph_url, data={
            'access_token': page_token, 
            'upload_phase': 'finish', 
            'upload_session_id': upload_session_id, 
            'description': f"{spun_title}\n\n{spun_desc}", 
            'media_type': 'REELS', 
            'video_state': 'PUBLISHED'
        }).json()
        
        print(f"Respon Finish [{page_name}]: {json.dumps(finish_res)}")
        
        new_video_id = finish_res.get('id') or finish_res.get('video_id')
        if finish_res.get('success') or new_video_id:
            if new_video_id and (spun_comment or video_link):
                final_comment = spun_comment if spun_comment else ""
                if video_link:
                    final_comment += f"\n{video_link}" if final_comment else video_link
                try:
                    time.sleep(2)
                    comm_res = requests.post(f"https://graph.facebook.com/v26.0/{new_video_id}/comments", data={'access_token': page_token, 'message': final_comment}).json()
                    print(f"Komentar pancingan terkirim: {comm_res}")
                except Exception as ce:
                    print(f"Gagal kirim komentar: {ce}")
            print(f"BERHASIL UPLOAD KE: {page_name}")
            return True
        else:
            print(f"META MENOLAK UPLOAD [{page_name}]: {json.dumps(finish_res)}")
            return False
    except Exception as e:
        print(f"EXCEPTION SAAT UPLOAD KE {page_name}: {e}")
        return False

success_upload_count = 0
with ThreadPoolExecutor(max_workers=1) as executor:
    futures = {executor.submit(upload_to_single_page, page): page for page in pages_data}
    for future in as_completed(futures):
        if future.result():
            success_upload_count += 1

if success_upload_count > 0:
    videos[target_index]['status'] = 'completed'
    cleaned_videos = []
    completed_videos = [v for v in videos if v.get('status'] == 'completed']
    pending_videos = [v for v in videos if v.get('status'] == 'pending']
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

print("Proses skrip upload selesai.")
