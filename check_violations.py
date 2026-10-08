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
        report_data = {"last_check": "", "total_deleted": 0, "logs": [], "pages_status": []}
else:
    report_data = {"last_check": "", "total_deleted": 0, "logs": [], "pages_status": []}

current_logs = []
pages_status_list = []
deleted_count = 0

print(f"Memulai pengecekan untuk {len(pages_data)} Fanpage...")

for page in pages_data:
    page_token = page.get('token')
    page_id = page.get('id')
    page_name = page.get('name')
    
    if not page_token or not page_id:
        continue
        
    is_page_troubled = False
    trouble_reason = "Aman"

    videos_url = f"https://graph.facebook.com/v26.0/{page_id}/videos?fields=id,title,description,status,copyright_check_status,format&access_token={page_token}"
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
            video_title = video.get('title') or video.get('description') or f"Video ID: {video_id}"
            if len(video_title) > 40:
                video_title = video_title[:37] + "..."
            
            detail_url = f"https://graph.facebook.com/v26.0/{video_id}?fields=status,copyright_check_status,picture&access_token={page_token}"
            try:
                detail_res = requests.get(detail_url).json()
            except:
                continue
            
            status_check = detail_res.get('copyright_check_status', '').lower()
            video_status = detail_res.get('status', {}).get('video_status', '').lower()
            # Ambil link thumbnail gambar video sebelum dihapus
            video_thumb = detail_res.get('picture', '')
            
            if (
                status_check in ['rejected', 'block', 'infringement'] or 
                video_status in ['error', 'expired', 'processing_failed'] or
                'copyright' in str(detail_res).lower()
            ):
                is_page_troubled = True
                trouble_reason = "Terdeteksi Pelanggaran/Copyright"

                delete_url = f"https://graph.facebook.com/v26.0/{video_id}?access_token={page_token}"
                delete_res = requests.delete(delete_url).json()
                
                if delete_res.get('success'):
                    deleted_count += 1
                    log_entry = {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "page": page_name,
                        "video_id": video_id,
                        "title": video_title,
                        "thumbnail": video_thumb,
                        "status": "Berhasil Dihapus (Copyright)"
                    }
                    current_logs.append(log_entry)

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

report_data["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
report_data["total_deleted"] += deleted_count
report_data["logs"] = current_logs + report_data.get("logs", [])[:50]
report_data["pages_status"] = pages_status_list

with open(report_file, 'w') as f:
    json.dump(report_data, f, indent=4)

print("Selesai.")
