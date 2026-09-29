import os
import json
import requests

def upload_video_via_url(page_id, page_token, video_url, title, description):
    url = f"https://graph.facebook.com/v26.0/{page_id}/videos"
    payload = {
        'title': title,
        'description': description,
        'file_url': video_url,  # Facebook mengambil berkas langsung dari URL
        'access_token': page_token
    }
    response = requests.post(url, data=payload)
    return response.json()

def main():
    pages_json = os.environ.get('FB_PAGES_DATA')
    if not pages_json:
        raise ValueError("Error: Secret 'FB_PAGES_DATA' tidak ditemukan atau kosong!")

    pages = json.loads(pages_json)

    if not os.path.exists('videos.json'):
        raise FileNotFoundError("Error: File 'videos.json' tidak ditemukan!")

    with open('videos.json', 'r', encoding='utf-8') as f:
        videos = json.load(f)

    updated = False
    for video in videos:
        if video.get('status') == 'pending':
            video_url = video.get('url')
            title = video.get('title', '')
            description = video.get('description', '')

            print("==========================================")
            print(f"Memproses video: {title}")
            print(f"URL Direct MP4: {video_url}")
            print("==========================================")
            
            try:
                # Unggah ke seluruh halaman Facebook via file_url
                success_count = 0
                for page in pages:
                    print(f"Mengirim URL video ke halaman: {page['name']} ({page['id']})...")
                    res = upload_video_via_url(
                        page['id'],
                        page['token'],
                        video_url,
                        title,
                        description
                    )
                    
                    if 'id' in res:
                        print(f" -> Sukses! Video ID: {res['id']}")
                        success_count += 1
                    else:
                        print(f" -> Gagal unggah ke {page['name']}: {json.dumps(res)}")

                if success_count > 0:
                    video['status'] = 'completed'
                    updated = True
                    break
                else:
                    raise RuntimeError("Gagal mengunggah ke halaman Facebook. Periksa token/izin halaman Anda.")

            except Exception as e:
                raise RuntimeError(f"Gagal memproses video: {e}")

    if updated:
        with open('videos.json', 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        print("videos.json berhasil diperbarui menjadi completed.")

if __name__ == '__main__':
    main()
