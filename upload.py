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

# ================= OTAK BOT SPINTAX (DESKRIPSI OTOMATIS) =================
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

def generate_auto_caption(title):
    templates = [
        "Wah asli {keren banget|bikin penasaran|wajib nonton|seru abis} nih! 😍\n\n{Tonton sampai habis ya|Jangan di-skip|Tonton sampai akhir|Wajib tonton full} biar ga penasaran sama kelanjutannya.\n\n👇 {Cek link di kolom komentar buat info produknya!|Barang uniknya ada di komen ya!|Link pembelian cek di komentar pertama!|Yang mau barangnya langsung cek komentar ya!}",
        "{Gokil|Keren abis|Mantap banget|Parah sih ini} videonya! 🎬✨\n\n{Kira-kira gimana kelanjutannya ya?|Seru banget kan?|Bikin tegang nih.|Estetik banget parah.}\n\n🛒 {Yang mau barang estetiknya klik link di komentar!|Cek komentar pertama buat link produk!|Spill link produk ada di kolom komentar!}"
    ]
    return f"{title}\n\n" + process_spintax(random.choice(templates))

def generate_auto_comment(link):
    if not link:
        return ""
    templates = [
        "{Samaan yuk!|Buruan cek sebelum kehabisan!|Klik di sini buat beli barangnya:|Checkout sekarang di sini:}\n👉 {link}",
        "{Produk estetiknya bisa dibeli di sini ya:|Link produk lengkapnya ada di sini:|Spill barangnya bisa cek tautan ini ya:}\n👉 {link}"
    ]
    raw_comment = random.choice(templates)
    return process_spintax(raw_comment).replace('{link}', link)
# ========================================================================

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
    print("File videos.json tidak ditemukan.")
    exit(0)

try:
    with open(videos_file, 'r') as f:
        videos = json.load(f)
except:
    print("Gagal membaca file videos.json.")
    exit(0)

target_video = None
target_index = -1
for index, video in enumerate(videos):
    if video.get('status') == 'pending':
        if is_instant_upload and target_video_id_inst is not None:
            if str(video.get('id')) == str(target_video_id_inst):
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
    print("Tidak ada video pending/terjadwal untuk di-upload.")
    exit(0)

video_id_db = target_video.get('id')
video_url = target_video.get('url')
video_title = target_video.get('title', 'Video Reels')
video_desc_template = target_video.get('description', '')
video_comment_template = target_video.get('comment_text', '') 
video_link = target_video.get('redirect_link', '')   
video_targets = target_video.get('target_pages', [])

if not video_desc_template or video_desc_template.strip() == video_title.strip() or len(video_desc_template) < 15:
    print("Memicu Bot Pembuat Caption Otomatis...")
    video_desc_template = generate_auto_caption(video_title)

if video_link and not video_comment_template:
    print("Memicu Bot Pembuat Komentar Pancingan...")
    video_comment_template = generate_auto_comment(video_link)

if video_targets and "Semua" not in video_targets:
    pages_data = [p for p in all_pages if p.get('name') in video_targets]
else:
    pages_data = all_pages

raw_filename = 'raw_video.mp4'
output_filename = 'final_video.mp4'

for f_name in [raw_filename, output_filename]:
    if os.path.exists(f_name):
        os.remove(f_name)

print(f"Mengunduh video ID {video_id_db}...")
gdown.download(video_url, raw_filename, quiet=False)

if not os.path.exists(raw_filename) or os.path.getsize(raw_filename) < 1000:
    print("Gagal mengunduh video atau file korup.")
    exit(1)

time.sleep(2) 

print("🤖 Menjalankan Mutasi & Standardisasi Format Meta Reels...")
try:
    mutation_cmd = [
        'ffmpeg', '-i', raw_filename, 
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=brightness=0.01', 
        '-pix_fmt', 'yuv420p', 
        '-c:v', 'libx264', '-profile:v', 'main', '-crf', '26', '-preset', 'fast', 
        '-c:a', 'aac', '-b:a', '128k', '-ac', '2',
        '-map_metadata', '-1', 
        '-movflags', '+faststart', 
        output_filename, '-y'
    ]
    subprocess.run(mutation_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
except Exception as e:
    print(f"Mutasi FFmpeg gagal: {e}. Menggunakan file mentah...")
    output_filename = raw_filename

time.sleep(2)

file_size = os.path.getsize(output_filename)

def upload_to_single_page(page):
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name', 'Unknown')
    
    if not page_token or not page_id:
        return False

    spun_title = process_spintax(video_title)
    spun_desc = process_spintax(video_desc_template)
    spun_comment = process_spintax(video_comment_template)
    
    video_graph_url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
    try:
        print(f"START upload ke: {page_name} (Ukuran: {file_size} bytes)")
        start_res = requests.post(video_graph_url, data={'access_token': page_token, 'upload_phase': 'start', 'file_size': file_size, 'media_type': 'REELS'}).json()
        
        if 'upload_session_id' not in start_res:
            print(f"GAGAL START [{page_name}]: {start_res}")
            return False
            
        upload_session_id = start_res['upload_session_id']
        start_offset = int(start_res.get('start_offset', 0))
        end_offset = int(start_res.get('end_offset', file_size))
        
        print(f"🔄 Mentransfer video ke Meta secara bertahap (Chunking)...")
        with open(output_filename, 'rb') as video_file:
            while start_offset < file_size:
                chunk_size = end_offset - start_offset
                if chunk_size <= 0:
                    chunk_size = 2 * 1024 * 1024 
                
                video_file.seek(start_offset)
                chunk_data = video_file.read(chunk_size)
                
                transfer_res = requests.post(video_graph_url, data={
                    'access_token': page_token, 
                    'upload_phase': 'transfer', 
                    'upload_session_id': upload_session_id, 
                    'start_offset': start_offset
                }, files={'video_file_chunk': ('video.mp4', chunk_data, 'video/mp4')}).json()
                
                if 'error' in transfer_res:
                    print(f"❌ Error saat transfer potongan video: {transfer_res}")
                    return False
                    
                start_offset = int(transfer_res.get('start_offset', start_offset + chunk_size))
                end_offset = int(transfer_res.get('end_offset', start_offset + chunk_size))
                print(f"   -> Progress: {start_offset} / {file_size} bytes")
                if start_offset == end_offset or start_offset >= file_size:
                    break 
        
        print(f"✅ Upload 100% selesai, memicu FINISH untuk {page_name}...")
        finish_data = {
            'access_token': page_token, 
            'upload_phase': 'finish', 
            'upload_session_id': upload_session_id, 
            'description': spun_desc, 
            'media_type': 'REELS', 
            'video_state': 'PUBLISHED'
        }
        
        finish_res = requests.post(video_graph_url, data=finish_data).json()
        new_video_id = finish_res.get('id') or finish_res.get('video_id')
        
        if finish_res.get('success') or new_video_id:
            # ==== PERBAIKAN LOGIKA KOMENTAR ====
            if new_video_id and (spun_comment or video_link):
                final_comment = spun_comment if spun_comment else video_link
                
                print("⏳ Menunggu 20 detik agar Meta memproses video sebelum mengirim komentar...")
                time.sleep(20) # Jeda diperpanjang agar Meta tidak menolak komentar
                
                try:
                    comm_res = requests.post(f"https://graph.facebook.com/v19.0/{new_video_id}/comments", data={'access_token': page_token, 'message': final_comment}).json()
                    if comm_res.get('id'):
                        print(f"✅ Komentar Pancingan Berhasil Dikirim! ID: {comm_res['id']}")
                    else:
                        print(f"❌ Gagal kirim komentar. Respon Meta: {comm_res}")
                except Exception as ce:
                    print(f"❌ Error sistem saat kirim komentar: {ce}")
            # ====================================
            return True
        else:
            return False
    except Exception as e:
        print(f"Error fatal: {e}")
        return False

success_upload_count = 0
with ThreadPoolExecutor(max_workers=1) as executor:
    futures = {executor.submit(upload_to_single_page, page): page for page in pages_data}
    for future in as_completed(futures):
        if future.result():
            success_upload_count += 1

if success_upload_count > 0:
    videos[target_index]['status'] = 'completed'
    try:
        with open(videos_file, 'w') as f:
            json.dump(videos, f, indent=4)
    except:
        pass

for f_name in [raw_filename, output_filename]:
    if os.path.exists(f_name):
        os.remove(f_name)

print("Selesai.")
