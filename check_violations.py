import os
import json
from datetime import datetime
import requests

# Memuat data token dari secret GitHub PAGES_DATA
pages_data_env = os.environ.get('FB_PAGES_DATA', '[]')
try:
    pages_data = json.loads(pages_data_env)
except Exception as e:
    print(f"Error parsing FB_PAGES_DATA: {e}")
    pages_data = []

report_file = 'report.json'

# Memuat laporan riwayat lama jika sudah ada
if os.path.exists(report_file):
    try:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
    except:
        report_data = {"last_check": "", "total_deleted": 0, "logs": []}
else:
    report_data = {"last_check": "", "total_deleted": 0, "logs": []}

current_logs = []
deleted_count = 0

print(f"Memulai pengecekan pelanggaran untuk {len(pages_data)} Fanpage...")

for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        continue
        
    # Mengambil daftar video dari Fanpage
    videos_url = f"https://graph.facebook.com/v26.0/{page_id}/videos?access_token={page_token}"
    try:
        response = requests.get(videos_url).json()
    except Exception as e:
        print(f"Gagal koneksi ke halaman {page_name}: {e}")
        continue
    
    if 'data' in response:
        for video in response['data']:
            video_id = video.get('id')
            
            # Memeriksa status detail dan indikasi copyright/pembatasan video
            detail_url = f"https://graph.facebook.com/v26.0/{video_id}?fields=status,copyright_check_status,title&access_token={page_token}"
            try:
                detail_res = requests.get(detail_url).json()
            except:
                continue
            
            status_check = detail_res.get('copyright_check_status', '')
            video_status = detail_res.get('status', {}).get('video_status', '')
            
            # Kondisi jika video terkena pembatasan hak cipta atau error dari sistem Meta
            if status_check == 'rejected' or video_status == 'error':
                # Eksekusi penghapusan video yang melanggar
                delete_url = f"https://graph.facebook.com/v26.0/{video_id}?access_token={page_token}"
                delete_res = requests.delete(delete_url).json()
                
                if delete_res.get('success'):
                    deleted_count += 1
                    log_entry = {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "page": page_name,
                        "video_id": video_id,
                        "title": detail_res.get('title', 'Tanpa Judul'),
                        "status": "Berhasil Dihapus (Pelanggaran/Copyright)"
                    }
                    current_logs.append(log_entry)
                    print(f"[HAPUS] Video di {page_name} dihapus karena masalah hak cipta.")

# Memperbarui data file laporan
report_data["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
report_data["total_deleted"] += deleted_count
# Menggabungkan log baru ke urutan atas dan membatasi riwayat hingga 50 log terakhir
report_data["logs"] = current_logs + report_data.get("logs", [])[:50]

with open(report_file, 'w') as f:
    json.dump(report_data, f, indent=4)

print("Pengecekan selesai dan laporan berhasil diperbarui.")
