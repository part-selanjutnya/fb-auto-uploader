import os
import json
from datetime import datetime
import requests

pages_data_env = os.environ.get('FB_PAGES_DATA', '[]')
try:
    pages_data = json.loads(pages_data_env)
except:
    pages_data = []

report_file = 'report.json'

if os.path.exists(report_file):
    try:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
    except:
        report_data = {"last_check": "", "total_warnings": 0, "violations": [], "pages_status": []}
else:
    report_data = {"last_check": "", "total_warnings": 0, "violations": [], "pages_status": []}

current_violations = []
pages_status_list = []
warning_count = 0

print(f"Memulai pemindaian peringatan untuk {len(pages_data)} Fanpage...")

for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        continue
        
    is_page_troubled = False
    trouble_reason = "Aman"

    # Mengambil fields lengkap tanpa pemotongan teks judul/deskripsi
    videos_url = f"https://graph.facebook.com/v26.0/{page_id}/videos?fields=id,title,description,status,copyright_check_status,created_time,picture&access_token={page_token}"
    try:
        response = requests.get(videos_url).json()
    except Exception as e:
        pages_status_list.append({
            "name": page_name,
            "status": "Gagal Koneksi API",
            "badge": "warning"
        })
        continue
    
    if 'data' in response:
        for video in response['data']:
            video_id = video.get('id')
            # Mengambil judul/deskripsi secara penuh (tanpa dibatasi panjangnya agar informasi utuh)
            full_title = video.get('title') or video.get('description') or f"Video ID: {video_id}"
            
            # Format Tanggal dan Jam Upload lengkap
            raw_time = video.get('created_time', '')
            formatted_time = raw_time
            try:
                dt = datetime.strptime(raw_time, "%Y-%m-%dT%H:%M:%S%z")
                formatted_time = dt.strftime("%d %b %Y, Pukul %H:%M:%S WIB")
            except:
                pass

            detail_url = f"https://graph.facebook.com/v26.0/{video_id}?fields=status,copyright_check_status,picture&access_token={page_token}"
            try:
                detail_res = requests.get(detail_url).json()
            except:
                continue
            
            status_check = detail_res.get('copyright_check_status', '').lower()
            video_status = detail_res.get('status', {}).get('video_status', '').lower()
            video_thumb = detail_res.get('picture', '') or video.get('picture', '')
            
            # Deteksi pelanggaran tanpa menghapus otomatis
            if status_check in ['rejected', 'block', 'infringement'] or video_status in ['error', 'expired', 'processing_failed']:
                is_page_troubled = True
                trouble_reason = "Perlu Perhatian (Copyright/Error)"
                warning_count += 1

                violation_entry = {
                    "page_id": page_id,
                    "page_token": page_token,
                    "page_name": page_name,
                    "video_id": video_id,
                    "title": full_title,
                    "thumbnail": video_thumb,
                    "upload_time": formatted_time,
                    "status": "Terdeteksi Masalah"
                }
                current_violations.append(violation_entry)

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

report_data["last_check"] = datetime.now().strftime("%d %b %Y, %H:%M:%S WIB")
report_data["total_warnings"] = warning_count
report_data["violations"] = current_violations
report_data["pages_status"] = pages_status_list

with open(report_file, 'w') as f:
    json.dump(report_data, f, indent=4)

print("Pemindaian selesai.")
