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

# Memuat laporan lama jika ada
if os.path.exists(report_file):
    try:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
    except:
        report_data = {"last_check": "", "total_deleted": 0, "logs": [], "pages_status": []}
else:
    report_data = {"last_check": "", "total_deleted": 0, "logs": [], "pages_status": []}

current_logs = []
pages_status_list = []
deleted_count = 0

print(f"Memulai pengecekan menyeluruh untuk {len(pages_data)} Fanpage...")

for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        continue
        
    is_page_troubled = False
    trouble_reason = "Aman"

    # Periksa informasi umum atau status halaman (opsional tambahan endpoint akun)
    page_info_url = f"https://graph.facebook.com/v26.0/{page_id}?fields=name,account_status,disable_info&access_token={page_token}"
    try:
        p_info = requests.get(page_info_url).json()
        if 'disable_info' in p_info and p_info['disable_info']:
            is_page_troubled = true
            trouble_reason = "Halaman Dibatasi/Disable"
    except:
        pass

    # Mengambil daftar video dari Fanpage
    videos_url = f"https://graph.facebook.com/v26.0/{page_id}/videos?access_token={page_token}"
    try:
        response = requests.get(videos_url).json()
    except Exception as e:
        print(f"Gagal koneksi ke halaman {page_name}: {e}")
        pages_status_list.append({
            "name": page_name,
            "status": "Gagal Koneksi API",
            "badge": "warning"
        })
        continue
    
    if 'data' in response:
        for video in response['data']:
            video_id = video.get('id')
            
            # Memeriksa status detail video
            detail_url = f"https://graph.facebook.com/v26.0/{video_id}?fields=status,copyright_check_status,title&access_token={page_token}"
            try:
                detail_res = requests.get(detail_url).json()
            except:
                continue
            
            status_check = detail_res.get('copyright_check_status', '').lower()
            video_status = detail_res.get('status', {}).get('video_status', '').lower()
            
            # Kondisi deteksi pelanggaran / copyright / error
            if (
                status_check in ['rejected', 'block', 'infringement'] or 
                video_status in ['error', 'expired', 'processing_failed'] or
                'copyright' in str(detail_res).lower()
            ):
                is_page_troubled = True
                trouble_reason = "Terdeteksi Pelanggaran/Copyright"

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
                    print(f"[HAPUS] Video di {page_name} dihapus karena masalah copyright.")

    # Menentukan status akhir halaman
    if is_page_troubled:
        pages_status_list.append({
            "name": page_name,
            "status": trouble_reason,
            "badge": "danger"
        })
    else:
        pages_status_list.append({
            "name": page_name,
            "status": "Aman",
            "badge": "success"
        })

# Memperbarui data laporan utama
report_data["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
report_data["total_deleted"] += deleted_count
report_data["logs"] = current_logs + report_data.get("logs", [])[:50]
report_data["pages_status"] = pages_status_list

with open(report_file, 'w') as f:
    json.dump(report_data, f, indent=4)

print("Pengecekan selesai dan laporan status halaman berhasil diperbarui.")
